class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling bookings, payments, refunds, and status updates.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated] 
    
    def get_queryset(self):
        """Filter bookings based on logged-in user role and query params."""
        user = self.request.user
        payment_status = self.request.query_params.get("payment_status")
        emergency = self.request.query_params.get("emergency")

        bookings = Booking.objects.none()

        if user.role == "customer":
            bookings = Booking.objects.filter(customer=user)

        elif user.role == "locksmith":
            try:
                locksmith = Locksmith.objects.get(user=user)
                bookings = Booking.objects.filter(locksmith_service__locksmith=locksmith)
            except Locksmith.DoesNotExist:
                return Booking.objects.none()

        elif user.role == "admin":
            bookings = Booking.objects.all()

        # Apply filters if provided
        if payment_status:
            bookings = bookings.filter(payment_status=payment_status)

        if emergency in ["true", "false"]:
            bookings = bookings.filter(emergency=(emergency.lower() == "true"))

        return bookings
        

    
    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_authenticated:
            raise serializers.ValidationError({"error": "User must be authenticated to create a booking."})

        if user.role != "customer":
            raise serializers.ValidationError({"error": "Only customers can create bookings."})

        data = self.request.data
        locksmith_service_id = data.get('locksmith_service')
        try:
            locksmith_service = LocksmithServices.objects.get(id=locksmith_service_id)
        except LocksmithServices.DoesNotExist:
            raise serializers.ValidationError({"error": "Invalid locksmith service."})

        number_of_keys = int(data.get('number_of_keys', 0))
        additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")

        admin_settings = AdminSettings.objects.first()
        if not admin_settings:
            raise serializers.ValidationError({"error": "Admin settings not configured."})

        commission_amount = admin_settings.commission_amount or Decimal("0.00")
        percentage = admin_settings.percentage or Decimal("0.00")
        gst_percentage = admin_settings.gst_percentage or Decimal("0.00")

        base_price = locksmith_service.custom_price or Decimal("0.00")
        keys_total = number_of_keys * additional_key_price

        subtotal = base_price + keys_total

        percentage_amount = (subtotal * percentage) / Decimal("100")
        platform_income = commission_amount + percentage_amount

        gst_amount = (platform_income * gst_percentage) / Decimal("100")

        total_price = subtotal + platform_income + gst_amount

        # Get emergency value from request (default to False if not provided)
        emergency = data.get('emergency', False)
        if isinstance(emergency, str):
            emergency = emergency.lower() in ['true', '1', 'yes']  # Convert string to boolean

        serializer.save(
            customer=user,
            locksmith_service=locksmith_service,
            number_of_keys=number_of_keys,
            total_price=total_price,
            emergency=emergency
        )

        


    
    @action(detail=True, methods=['post'],permission_classes=[IsCustomer])
    def process_payment(self, request, pk=None):
        booking = self.get_object()

        # Use total_price directly from the booking model
        total_price = booking.total_price or 0.0
        locksmith_service = booking.locksmith_service

        if total_price <= 0:
            return Response({"error": "Total price must be greater than 0."}, status=400)

        try:
            # Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card", "afterpay_clearpay", "klarna", "zip"],
                line_items=[{
                    'price_data': {
                        'currency': 'aud',
                        'product_data': {
                            'name': locksmith_service.admin_service.name
                        },
                        'unit_amount': int(total_price * 100),  # Stripe uses cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url="https://lockquick.com.au/payment-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://lockquick.com.au/payment-cancel",
            )

            booking.stripe_session_id = checkout_session.id
            booking.payment_status = "pending"
            booking.save()

            return Response({'checkout_url': checkout_session.url})

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)


    @action(detail=True, methods=['post'],permission_classes=[IsCustomer])
    def complete_payment(self, request, pk=None):
        booking = self.get_object()

        if not booking.stripe_session_id:
            return Response({"error": "Missing Stripe Session ID."}, status=400)

        try:
            session = stripe.checkout.Session.retrieve(booking.stripe_session_id)

            if session.payment_status == "paid":
                booking.payment_intent_id = session.payment_intent
                booking.payment_status = "paid"
                booking.status = "Scheduled"
                booking.save()

                locksmith = booking.locksmith_service.locksmith
                customer = booking.customer

                # ✅ Send SMS to customer: payment success, wait for approval
                customer_message = (
                    f"Hello {customer.get_full_name()},\n"
                    f"Your payment for the booking (ID: {booking.id}) is successful.\n"
                    f"Please wait for the locksmith to approve your request.\n"
                    f"You will be notified once it's approved or denied."
                )
                send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

                # ✅ Notify locksmith about the new booking
                locksmith_message = (
                    f"Hello {locksmith.user.get_full_name()},\n"
                    f"You have a new booking (ID: {booking.id}) from customer {customer.get_full_name()}.\n"
                    f"Service: {booking.locksmith_service.admin_service.name}\n"
                    # f"Customer Address: {booking.customer_address or 'N/A'}\n"
                    # f"Customer Phone: {booking.customer_contact_number or customer.phone_number or 'N/A'}\n"
                    f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Emergency Service: {'Yes' if booking.emergency else 'No'}\n"
                    f"Please approve or deny this booking."
                    f"Thank you."
                )
                send_sms(locksmith.contact_number, locksmith_message)

                return Response({
                    "status": "Payment confirmed and booking scheduled.",
                    "message": "SMS notifications sent to customer and locksmith."
                })

            return Response({"error": "Payment is not completed yet."}, status=400)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)
        
        
        
    @action(detail=True, methods=['post'], permission_classes=[IsLocksmith])
    def approve_booking(self, request, pk=None):
        booking = self.get_object()
        user = request.user

        if user.role != 'locksmith':
            return Response({'error': 'Only locksmiths can approve bookings.'}, status=403)

        if booking.locksmith_status != 'PENDING':
            return Response({'error': 'Booking has already been responded to.'}, status=400)

        if booking.payment_status != 'paid':
            return Response({'error': 'Cannot approve booking. Payment is not completed.'}, status=400)

        booking.locksmith_status = 'APPROVED'
        booking.save()

        customer = booking.customer
        locksmith = booking.locksmith_service.locksmith

        # Notify customer
        customer_message = (
            f"Hello {customer.get_full_name()},\n"
            f"Your booking (ID: {booking.id}) has been accepted by the locksmith.\n"
            f"Locksmith: {locksmith.user.get_full_name()}\n"
            f"Contact: {locksmith.contact_number}\n"
            f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
            f"Thank you for choosing our service!"
        )
        send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

        # Notify locksmith again (optional)
        locksmith_message = (
            f"Hello {locksmith.user.get_full_name()},\n"
            f"Your approved service details are here:\n"
            f"Booking ID: {booking.id}\n"
            f"Customer: {customer.get_full_name()}\n"
            f"Service: {booking.locksmith_service.admin_service.name}\n"
            f"Customer Address: {booking.customer_address or 'N/A'}\n"
            f"Customer Phone: {booking.customer_contact_number or customer.phone_number or 'N/A'}\n"
            f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
            f"Emergency Service: {'Yes' if booking.emergency else 'No'}\n"
            f"Thank you.\n"
        )
        send_sms(locksmith.contact_number, locksmith_message)

        return Response({'status': 'Booking approved and customer notified.'})

    @action(detail=True, methods=['post'], permission_classes=[IsLocksmith])
    def deny_booking(self, request, pk=None):
        booking = self.get_object()
        user = request.user

        if user.role != 'locksmith':
            return Response({'error': 'Only locksmiths can deny bookings.'}, status=403)

        if booking.locksmith_status != 'PENDING':
            return Response({'error': 'Booking has already been responded to.'}, status=400)

        if booking.payment_status != 'paid':
            return Response({'error': 'Cannot deny booking. Payment is not completed.'}, status=400)

        booking.locksmith_status = 'DENIED'
        booking.status = 'Cancelled'
        booking.payment_status = 'refunded'
        booking.save()

        customer = booking.customer

        # Notify customer about denial
        customer_message = (
            f"Hello {customer.get_full_name()},\n"
            f"Your booking (ID: {booking.id}) has been denied by the locksmith.\n"
            f"A refund will be processed, and you may choose another service provider from LockQuick.\n"
            f"Visit https://lockquick.com.au/ to book again.\n"
            f"Thank you for choosing LockQuick."
        )
        send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

        # TODO: Implement Stripe refund logic here

        return Response({'status': 'Booking denied and customer notified.'})




    
    @action(detail=True, methods=['post'], permission_classes=[IsLocksmith])
    def complete(self, request, pk=None):
        """
        Locksmith marks booking as completed and receives payment
        """
        booking = self.get_object()
        locksmith_service = booking.locksmith_service
        locksmith = locksmith_service.locksmith

        # Check if locksmith_status is APPROVED
        if booking.locksmith_status != "APPROVED":
            return Response(
                {'error': 'Booking must be approved by the locksmith before completion.'},
                status=400
            )

        # Check booking status
        if booking.status != "Scheduled":
            return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

        # Check payment intent exists
        if not booking.payment_intent_id:
            return Response({'error': 'No PaymentIntent ID found. Ensure payment is completed.'}, status=400)

        # Check locksmith ownership
        if locksmith.user != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        # Check locksmith Stripe account
        if not locksmith.stripe_account_id:
            return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

        try:
            # Retrieve PaymentIntent from Stripe
            payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

            if payment_intent.status == "succeeded":
                # Get admin settings
                admin_settings = AdminSettings.objects.first()
                commission_amount = admin_settings.commission_amount or Decimal("0.00")
                percentage = admin_settings.percentage or Decimal("0.00")
                gst_percentage = admin_settings.gst_percentage or Decimal("0.00")

                # Calculate base price + additional keys
                base_price = locksmith_service.custom_price or Decimal("0.00")
                number_of_keys = booking.number_of_keys or 0
                additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")
                keys_total = additional_key_price * Decimal(number_of_keys)

                subtotal = base_price + keys_total

                # Platform % fee
                percentage_amount = (subtotal * percentage) / Decimal("100")

                # Platform income = fixed + %
                platform_income = commission_amount + percentage_amount

                # GST on platform income
                gst_amount = (platform_income * gst_percentage) / Decimal("100")

                # Total price (already stored in booking)
                total_price = booking.total_price or Decimal("0.00")

                # Now: Transfer only base_price + keys_total to locksmith (not platform fees, not GST)
                transfer_amount = base_price + keys_total

                if transfer_amount <= 0:
                    return Response({'error': 'Transfer amount is zero or negative after deductions.'}, status=400)

                # Convert to cents for Stripe
                transfer_amount_cents = int(transfer_amount * Decimal('100'))

                # Perform Stripe Transfer
                stripe.Transfer.create(
                    amount=transfer_amount_cents,
                    currency="aud",
                    destination=locksmith.stripe_account_id,
                    transfer_group=f"booking_{booking.id}"
                )

                # Update booking status and payment_status
                booking.status = "Completed"
                booking.payment_status = "paid"
                booking.save()

                # Return response with breakdown
                return Response({
                    'status': 'Booking completed and payment transferred to locksmith',
                    'total_price': str(total_price),
                    'locksmith_transfer_amount': str(transfer_amount),
                    'locksmith_charges': str(base_price),
                    'additional_key_charges': str(keys_total),
                    'platform_charges': str(commission_amount),
                    'service_charges': str(percentage_amount),
                    'gst': str(gst_amount),
                    'platform_income': str(platform_income),
                })

            else:
                return Response({'error': f'Invalid PaymentIntent status: {payment_intent.status}'}, status=400)

        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=400)






    @action(detail=True, methods=['post'])
    def process_refund(self, request, pk=None):
        """Refund customer payment."""
        booking = self.get_object()

        if not booking.payment_intent_id:
            return Response({"error": "PaymentIntent ID is missing."}, status=400)

        try:
            refund = stripe.Refund.create(payment_intent=booking.payment_intent_id)
            booking.payment_status = "refunded"
            booking.save()

            return Response({"message": "Refund successful", "refund_id": refund.id})

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Customer cancels the booking."""
        booking = self.get_object()
        if booking.customer != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        if booking.payment_status == "pending":
            try:
                stripe.PaymentIntent.cancel(booking.payment_intent_id)
            except stripe.error.StripeError:
                return Response({'error': 'Failed to cancel payment'}, status=400)

        booking.payment_status = "canceled"
        booking.save()
        return Response({'status': 'Booking canceled'})

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """List bookings for the authenticated user."""
        user = request.user
        if user.role == "customer":
            bookings = Booking.objects.filter(customer=user,payment_status='paid')
        elif user.role == "locksmith":
            try:
                locksmith = Locksmith.objects.get(user=user)
                bookings = Booking.objects.filter(locksmith_service__locksmith=locksmith,
                payment_status='paid')
            except Locksmith.DoesNotExist:
                return Response({"error": "No locksmith profile found"}, status=400)
        elif user.role == "admin":
            bookings = Booking.objects.all()
        else:
            return Response({"error": "Unauthorized"}, status=403)

        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

