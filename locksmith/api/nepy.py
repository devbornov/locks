    # Twilio Credentials (Replace with actual credentials)
TWILIO_ACCOUNT_SID = "ACba1e3f20eb7083c73471a9e87c04802c"
TWILIO_AUTH_TOKEN = "ca2a6daa04eed144e8bb9af1269a265e"
TWILIO_PHONE_NUMBER = "+12233572123"

def call_locksmith(locksmith_phone, locksmith_name, booking_id):
    """Function to call the locksmith after successful payment."""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    message = f"Hello {locksmith_name}, you have received a new booking. Booking ID: {booking_id}. Please check your dashboard for details."
    
    call = client.calls.create(
        twiml=f'<Response><Say>{message}</Say></Response>',
        to=locksmith_phone,
        from_=TWILIO_PHONE_NUMBER
    )
    
    print(f"📞 Call triggered to Locksmith {locksmith_name} (Phone: {locksmith_phone}) - Call SID: {call.sid}")
    return call.sid


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

        base_price = locksmith_service.custom_price or Decimal("0.00")
        keys_total = number_of_keys * additional_key_price

        subtotal = base_price + keys_total
        percentage_amount = (subtotal * percentage) / Decimal("100")
        total_price = subtotal + percentage_amount + commission_amount

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
        

    
    @action(detail=True, methods=['post'])
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

    
    
    @action(detail=True, methods=['post'])
    def complete_payment(self, request, pk=None):
        print(f"complete_payment called with pk={pk}")

        # Manual fetch to debug get_object issue
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=404)

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
        """
        Locksmith marks booking as completed and receives payment
        """
        booking = self.get_object()
        locksmith_service = booking.locksmith_service
        locksmith = locksmith_service.locksmith

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

                # Calculate subtotal: base price + additional keys cost
                base_price = locksmith_service.custom_price or Decimal("0.00")
                number_of_keys = booking.number_of_keys or 0
                additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")
                keys_total = additional_key_price * Decimal(number_of_keys)

                subtotal = base_price + keys_total

                # Calculate percentage amount (commission)
                percentage_amount = (subtotal * percentage) / Decimal("100")

                # Calculate transfer amount = total_price - percentage_amount - commission_amount
                total_price = booking.total_price or Decimal("0.00")
                transfer_amount = total_price - percentage_amount - commission_amount

                if transfer_amount <= 0:
                    return Response({'error': 'Transfer amount is zero or negative after deductions.'}, status=400)

                # Convert to cents for Stripe
                transfer_amount_cents = int(transfer_amount * Decimal('100'))

                # Transfer payment to locksmith Stripe account
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

                return Response({
                    'status': 'Booking completed and payment transferred to locksmith',
                    'total_price': str(total_price),
                    'subtotal': str(subtotal),
                    'percentage_amount': str(percentage_amount),
                    'commission_amount': str(commission_amount),
                    'transfer_amount': str(transfer_amount)
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



@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    print("📦 Raw Payload:", payload)  # Debug

    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        print("❌ Webhook error:", str(e))
        return HttpResponse(status=400)

    print("✅ Event type:", event['type'])

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        print("🔎 Session ID:", session_id)

        try:
            booking = Booking.objects.get(stripe_session_id=session_id)
            booking.payment_status = 'paid'
            booking.payment_intent_id = session.get('payment_intent')
            booking.save()
            print(f"✅ Booking {booking.id} marked as paid via webhook.")
        except Booking.DoesNotExist:
            print(f"❌ Booking not found for session ID: {session_id}")
            return JsonResponse({"error": "Booking not found"}, status=404)

    return HttpResponse(status=200)