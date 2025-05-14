class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling bookings, payments, refunds, and status updates.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated] 
    
    def get_queryset(self):
        """Filter bookings based on logged-in user role."""
        user = self.request.user  

        if user.role == "customer":
            return Booking.objects.filter(customer=user)

        elif user.role == "locksmith":
            try:
                locksmith = Locksmith.objects.get(user=user)  
                return Booking.objects.filter(locksmith_service__locksmith=locksmith)  
            except Locksmith.DoesNotExist:
                return Booking.objects.none()  

        elif user.role == "admin":
            return Booking.objects.all()  

        return Booking.objects.none() 
        
    # def perform_create(self, serializer):
    #     user = self.request.user

    #     if not user.is_authenticated:
    #         raise serializers.ValidationError({"error": "User must be authenticated to create a booking."})

    #     if user.role != "customer":
    #         raise serializers.ValidationError({"error": "Only customers can create bookings."})

    #     customer_contact_number = self.request.data.get('customer_contact_number')
    #     customer_address = self.request.data.get('customer_address')
    #     house_number = self.request.data.get('house_number')
    #     number_of_keys = self.request.data.get('number_of_keys')

    #     serializer.save(
    #         customer=user,
    #         customer_contact_number=customer_contact_number,
    #         customer_address=customer_address,
    #         house_number=house_number,
    #         number_of_keys=number_of_keys
    #     )

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
        cost_per_key = 10.0  # Fixed cost per key (you can make this dynamic later)

        base_price = locksmith_service.total_price or 0.0
        key_total = number_of_keys * cost_per_key
        total_price = base_price + key_total

        booking = serializer.save(
            customer=user,
            locksmith_service=locksmith_service,
            number_of_keys=number_of_keys,
            total_price=total_price,
        )
    
    
    
    # @action(detail=True, methods=['post'])
    # def process_payment(self, request, pk=None):
    #     booking = self.get_object()
    #     locksmith_service = booking.locksmith_service  
    #     total_price = locksmith_service.total_price  

    #     try:
    #         checkout_session = stripe.checkout.Session.create(
    #             payment_method_types=["card", "afterpay_clearpay", "klarna", "zip"],
    #             line_items=[{
    #                 'price_data': {
    #                     'currency': 'aud',
    #                     'product_data': {'name': locksmith_service.admin_service.name},
    #                     'unit_amount': int(total_price * 100),
    #                 },
    #                 'quantity': 1,
    #             }],
    #             mode='payment',
    #             success_url="https://lockquick.com.au/payment-success?session_id={CHECKOUT_SESSION_ID}",
    #             cancel_url="https://lockquick.com.au/payment-cancel",
    #         )

    #         booking.stripe_session_id = checkout_session.id
    #         booking.payment_status = "pending"
    #         booking.save()

    #         return Response({'checkout_url': checkout_session.url})

    #     except stripe.error.StripeError as e:
    #         return Response({"error": str(e)}, status=400)
    

    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        booking = self.get_object()
        locksmith_service = booking.locksmith_service

        # Safely get service price from service model
        service_price = locksmith_service.total_price or 0.0

        # Safely get key price from booking model
        key_price = booking.key_price or 0.0

        # Calculate combined total
        combined_total = service_price + key_price

        # Save combined total to booking model
        booking.total_price = combined_total
        booking.save()

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
                        'unit_amount': int(combined_total * 100),  # Stripe uses cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url="https://lockquick.com.au/payment-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://lockquick.com.au/payment-cancel",
            )

            # Save Stripe session to booking
            booking.stripe_session_id = checkout_session.id
            booking.payment_status = "pending"
            booking.save()

            return Response({'checkout_url': checkout_session.url})

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

    
    @action(detail=True, methods=['post'])
    def complete_payment(self, request, pk=None):
        """Handles payment completion without using Stripe webhook."""
        booking = self.get_object()

        if not booking.stripe_session_id:
            return Response({"error": "Missing Stripe Session ID."}, status=400)

        try:
            # Retrieve Stripe Checkout Session
            session = stripe.checkout.Session.retrieve(booking.stripe_session_id)

            if session.payment_status == "paid":
                booking.payment_intent_id = session.payment_intent
                booking.payment_status = "paid"
                booking.status = "Scheduled"
                booking.save()

                locksmith = booking.locksmith_service.locksmith
                # call_locksmith(locksmith.contact_number, locksmith.user.get_full_name(), booking.id)

                return Response({
                    "status": "Payment confirmed and booking scheduled.",
                    "message": "Locksmith notified via automated call."
                })

            return Response({"error": "Payment is not completed yet."}, status=400)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)
    

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Locksmith marks booking as completed and receives payment"""
        booking = self.get_object()

        # ✅ Ensure booking is scheduled
        if booking.status != "Scheduled":
            return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

        # ✅ Ensure payment exists
        if not booking.payment_intent_id:
            return Response({'error': 'No PaymentIntent ID found. Ensure payment is completed.'}, status=400)

        # ✅ Ensure locksmith is correct
        locksmith = booking.locksmith_service.locksmith
        if locksmith.user != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        # ✅ Ensure locksmith has Stripe account
        if not locksmith.stripe_account_id:
            return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

        try:
            # ✅ Retrieve PaymentIntent
            payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

            # ✅ If payment is already captured, transfer funds
            if payment_intent.status == "succeeded":
                price_per_key = 10.00
                num_keys = booking.number_of_keys or 0
                key_cost = num_keys * price_per_key

                total_price = booking.locksmith_service.total_price + key_cost
                custom_price = booking.locksmith_service.custom_price

                deduct_amount = total_price - custom_price
                transfer_amount = custom_price + key_cost  
                transfer_amount_cents = int(transfer_amount * 100)

                # ✅ Transfer money to locksmith
                transfer = stripe.Transfer.create(
                    amount=transfer_amount_cents,
                    currency="aud",
                    destination=locksmith.stripe_account_id,
                    transfer_group=f"booking_{booking.id}"
                )

                # ✅ Mark booking as completed
                booking.status = "Completed"
                booking.payment_status = "paid"
                booking.save()

                return Response({
                    'status': 'Booking completed and payment transferred to locksmith',
                    'transfer_amount': transfer_amount,
                    'deducted_amount': deduct_amount
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
            bookings = Booking.objects.filter(customer=user)
        elif user.role == "locksmith":
            try:
                locksmith = Locksmith.objects.get(user=user)
                bookings = Booking.objects.filter(locksmith_service__locksmith=locksmith)
            except Locksmith.DoesNotExist:
                return Response({"error": "No locksmith profile found"}, status=400)
        elif user.role == "admin":
            bookings = Booking.objects.all()
        else:
            return Response({"error": "Unauthorized"}, status=403)

        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)