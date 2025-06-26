#     # Twilio Credentials (Replace with actual credentials)
# TWILIO_ACCOUNT_SID = "ACba1e3f20eb7083c73471a9e87c04802c"
# TWILIO_AUTH_TOKEN = "ca2a6daa04eed144e8bb9af1269a265e"
# TWILIO_PHONE_NUMBER = "+12233572123"

# def call_locksmith(locksmith_phone, locksmith_name, booking_id):
#     """Function to call the locksmith after successful payment."""
#     client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
#     message = f"Hello {locksmith_name}, you have received a new booking. Booking ID: {booking_id}. Please check your dashboard for details."
    
#     call = client.calls.create(
#         twiml=f'<Response><Say>{message}</Say></Response>',
#         to=locksmith_phone,
#         from_=TWILIO_PHONE_NUMBER
#     )
    
#     print(f"📞 Call triggered to Locksmith {locksmith_name} (Phone: {locksmith_phone}) - Call SID: {call.sid}")
#     return call.sid





from twilio.rest import Client

TWILIO_ACCOUNT_SID = "ACb9993d68e0c490eb54de4f61018d5691"
TWILIO_AUTH_TOKEN = "6e7b89c3e473c1a92a9d31e6868fee66"
TWILIO_PHONE_NUMBER = "+12185229562"

def send_sms(to_phone, message):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    sms = client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to_phone
    )
    print(f"📩 SMS sent to {to_phone} - SID: {sms.sid}")
    return sms.sid


# class BookingViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for handling bookings, payments, refunds, and status updates.
#     """
#     queryset = Booking.objects.all()
#     serializer_class = BookingSerializer
#     permission_classes = [IsAuthenticated] 
    
#     def get_queryset(self):
#         """Filter bookings based on logged-in user role."""
#         user = self.request.user  

#         if user.role == "customer":
#             return Booking.objects.filter(customer=user)

#         elif user.role == "locksmith":
#             try:
#                 locksmith = Locksmith.objects.get(user=user)  
#                 return Booking.objects.filter(locksmith_service__locksmith=locksmith)  
#             except Locksmith.DoesNotExist:
#                 return Booking.objects.none()  

#         elif user.role == "admin":
#             return Booking.objects.all()  

#         return Booking.objects.none() 
        
#     def perform_create(self, serializer):
#         """
#         Assign the authenticated user as the customer before saving.
#         """
#         user = self.request.user

#         if not user.is_authenticated:
#             raise serializers.ValidationError({"error": "User must be authenticated to create a booking."})

#         if user.role != "customer":
#             raise serializers.ValidationError({"error": "Only customers can create bookings."})

#         # Get additional fields from request data
#         customer_contact_number = self.request.data.get('customer_contact_number')
#         customer_address = self.request.data.get('customer_address')
#         house_number = self.request.data.get('house_number')  # ✅ new field

#         # Debug prints to check the values before saving
#         print("Customer Contact Number:", customer_contact_number)
#         print("Customer Address:", customer_address)
#         print("House Number:", house_number)

#         # Save the booking with the provided data
#         serializer.save(
#             customer=user,
#             customer_contact_number=customer_contact_number,
#             customer_address=customer_address,
#             house_number=house_number  # ✅ include in save
#         )
        
        
        

    
#     @action(detail=True, methods=['post'])
#     def process_payment(self, request, pk=None):
#         booking = self.get_object()
#         locksmith_service = booking.locksmith_service  
#         total_price = locksmith_service.total_price  

#         try:
#             checkout_session = stripe.checkout.Session.create(
#                 payment_method_types=["card", "afterpay_clearpay", "klarna", "zip"],
#                 line_items=[{
#                     'price_data': {
#                         'currency': 'aud',
#                         'product_data': {'name': locksmith_service.admin_service.name},
#                         'unit_amount': int(total_price * 100),  # Convert to cents
#                     },
#                     'quantity': 1,
#                 }],
#                 mode='payment',
#                 success_url="https://lockquick.com.au/payment-success?session_id={CHECKOUT_SESSION_ID}",
#                 cancel_url="https://lockquick.com.au/payment-cancel",
#             )

#             # 🔹 Save Stripe Session ID in Booking
#             booking.stripe_session_id = checkout_session.id
#             booking.payment_status = "pending"
#             booking.save()

#             print(f"✅ Saved Booking {booking.id} with Stripe Session ID: {checkout_session.id}")

#             return Response({'checkout_url': checkout_session.url})

#         except stripe.error.StripeError as e:
#             return Response({"error": str(e)}, status=400)
    
#     @action(detail=True, methods=['post'])
#     def complete_payment(self, request, pk=None):
#         """Handles payment completion and triggers a call to the locksmith."""
#         booking = self.get_object()
        
#         # Ensure payment was made
#         if not booking.payment_intent_id:
#             return Response({"error": "No PaymentIntent ID found. Ensure payment is completed."}, status=400)

#         try:
#             # Retrieve PaymentIntent
#             payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

#             if payment_intent.status == "succeeded":
#                 booking.payment_status = "paid"
#                 booking.status = "Scheduled"
#                 booking.save()
                
#                 # 🔹 Trigger a call to the locksmith
#                 locksmith = booking.locksmith_service.locksmith
#                 call_locksmith(locksmith.contact_number, locksmith.user.get_full_name(), booking.id)

#                 return Response({
#                     "status": "Payment successful. Booking confirmed.",
#                     "message": "Locksmith has been notified via an automated call."
#                 })

#             return Response({"error": "Payment not completed."}, status=400)

#         except stripe.error.StripeError as e:
#             return Response({"error": str(e)}, status=400)
        

#     @action(detail=True, methods=['post'])
#     def complete(self, request, pk=None):
#         """Locksmith marks booking as completed and receives payment"""
#         booking = self.get_object()

#         # ✅ Ensure booking is scheduled
#         if booking.status != "Scheduled":
#             return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

#         # ✅ Ensure payment exists
#         if not booking.payment_intent_id:
#             return Response({'error': 'No PaymentIntent ID found. Ensure payment is completed.'}, status=400)

#         # ✅ Ensure locksmith is correct
#         locksmith = booking.locksmith_service.locksmith
#         if locksmith.user != request.user:
#             return Response({'error': 'Permission denied'}, status=403)

#         # ✅ Ensure locksmith has Stripe account
#         if not locksmith.stripe_account_id:
#             return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

#         try:
#             # ✅ Retrieve PaymentIntent
#             payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

#             # ✅ If payment is already captured, transfer funds
#             if payment_intent.status == "succeeded":
#                 total_price = booking.locksmith_service.total_price
#                 custom_price = booking.locksmith_service.custom_price

#                 # ✅ Deduction Calculation
#                 deduct_amount = total_price - custom_price
#                 transfer_amount = custom_price  # Only sending locksmith's custom price

#                 # ✅ Convert to cents
#                 transfer_amount_cents = int(transfer_amount * 100)

#                 # ✅ Transfer money to locksmith
#                 transfer = stripe.Transfer.create(
#                     amount=transfer_amount_cents,
#                     currency="usd",
#                     destination=locksmith.stripe_account_id,
#                     transfer_group=f"booking_{booking.id}"
#                 )

#                 # ✅ Mark booking as completed
#                 booking.status = "Completed"
#                 booking.payment_status = "paid"
#                 booking.save()

#                 return Response({
#                     'status': 'Booking completed and payment transferred to locksmith',
#                     'transfer_amount': transfer_amount,
#                     'deducted_amount': deduct_amount
#                 })
                

#             else:
#                 return Response({'error': f'Invalid PaymentIntent status: {payment_intent.status}'}, status=400)

#         except stripe.error.StripeError as e:
#             return Response({'error': str(e)}, status=400)




#     @action(detail=True, methods=['post'])
#     def process_refund(self, request, pk=None):
#         """
#         ✅ Refund customer payment.
#         """
#         booking = self.get_object()

#         if not booking.payment_intent_id:
#             return Response({"error": "PaymentIntent ID is missing."}, status=400)

#         try:
#             refund = stripe.Refund.create(payment_intent=booking.payment_intent_id)

#             booking.payment_status = "refunded"
#             booking.save()

#             return Response({"message": "Refund successful", "refund_id": refund.id})

#         except stripe.error.StripeError as e:
#             return Response({"error": str(e)}, status=400)

#     @action(detail=True, methods=['post'])
#     def cancel(self, request, pk=None):
#         """
#         ✅ Customer cancels the booking.
#         """
#         booking = self.get_object()
#         if booking.customer != request.user:
#             return Response({'error': 'Permission denied'}, status=403)
        
#         if booking.payment_status == "pending":
#             try:
#                 # ✅ Cancel Stripe Payment Intent if funds are held
#                 stripe.PaymentIntent.cancel(booking.payment_intent_id)
#             except stripe.error.StripeError:
#                 return Response({'error': 'Failed to cancel payment'}, status=400)

#         booking.payment_status = "canceled"
#         booking.save()
#         return Response({'status': 'Booking canceled'})

#     @action(detail=False, methods=['get'])
#     def my_bookings(self, request):
#         """
#         ✅ List bookings for the authenticated user.
#         """
#         user = request.user
#         if user.role == "customer":
#             bookings = Booking.objects.filter(customer=user)
#         elif user.role == "locksmith":
#             try:
#                 locksmith = Locksmith.objects.get(user=user)
#                 bookings = Booking.objects.filter(locksmith_service__locksmith=locksmith)
#             except Locksmith.DoesNotExist:
#                 return Response({"error": "No locksmith profile found"}, status=400)
#         elif user.role == "admin":
#             bookings = Booking.objects.all()
#         else:
#             return Response({"error": "Unauthorized"}, status=403)

#         serializer = self.get_serializer(bookings, many=True)
#         return Response(serializer.data)
    
    
    
# STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET  

# @csrf_exempt
# def stripe_webhook(request):
#     print("\n🔹 Webhook Received!")  # ✅ Log that webhook is received

#     payload = request.body
#     sig_header = request.headers.get("Stripe-Signature", None)

#     try:
#         # ✅ Verify Stripe Signature
#         event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
#         print(f"\n🔹 Full Webhook Event:\n{json.dumps(event, indent=2)}")  # ✅ Log full event
#     except ValueError as e:
#         print(f"\n❌ Invalid Payload: {str(e)}")
#         return JsonResponse({"error": "Invalid payload"}, status=400)
#     except stripe.error.SignatureVerificationError as e:
#         print(f"\n❌ Invalid Signature: {str(e)}")
#         return JsonResponse({"error": "Invalid signature"}, status=400)

#     # ✅ Process "checkout.session.completed" Event
#     if event["type"] == "checkout.session.completed":
#         session = event["data"]["object"]
#         stripe_session_id = session.get("id")  # ✅ Get Stripe Session ID
#         payment_intent_id = session.get("payment_intent")

#         print(f"\n🔹 Processing PaymentIntent ID: {payment_intent_id}")

#         # ✅ Find and Update Booking using Stripe Session ID
#         booking = Booking.objects.filter(stripe_session_id=stripe_session_id).first()

#         if booking:
#             booking.payment_intent_id = payment_intent_id  # ✅ Save Payment Intent ID
#             booking.payment_status = "paid"  # ✅ Mark as Paid
#             booking.save()
#             print(f"\n✅ Updated Booking {booking.id} with PaymentIntent ID: {payment_intent_id}")
#         else:
#             print("\n❌ No matching booking found for this payment!")

#     return HttpResponse(status=200)







class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling bookings, payments, refunds, and status updates.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated] 
    
    def get_queryset(self):
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

        # ✅ Explicitly order by ID (ascending)
        return bookings.order_by('id')
        
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

    # def perform_create(self, serializer):
    #     user = self.request.user

    #     if not user.is_authenticated:
    #         raise serializers.ValidationError({"error": "User must be authenticated to create a booking."})

    #     if user.role != "customer":
    #         raise serializers.ValidationError({"error": "Only customers can create bookings."})

    #     data = self.request.data
    #     locksmith_service_id = data.get('locksmith_service')
    #     try:
    #         locksmith_service = LocksmithServices.objects.get(id=locksmith_service_id)
    #     except LocksmithServices.DoesNotExist:
    #         raise serializers.ValidationError({"error": "Invalid locksmith service."})

    #     number_of_keys = int(data.get('number_of_keys', 0))
    #     additional_key_price = locksmith_service.additional_key_price or 0.0

    #     base_price = locksmith_service.total_price or 0.0
    #     key_total = number_of_keys * additional_key_price
    #     total_price = base_price + key_total

    #     booking = serializer.save(
    #         customer=user,
    #         locksmith_service=locksmith_service,
    #         number_of_keys=number_of_keys,
    #         total_price=total_price,
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
                # success_url="https://lockquick.com.au/payment-success?session_id={CHECKOUT_SESSION_ID}",
                success_url="http://localhost:3000/payment-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://lockquick.com.au/payment-cancel",
            )

            booking.stripe_session_id = checkout_session.id
            booking.payment_status = "pending"
            booking.save()

            return Response({'checkout_url': checkout_session.url})

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

    # @action(detail=True, methods=['post'])
    # def complete(self, request, pk=None):
    #     """Locksmith marks booking as completed and receives payment"""
    #     booking = self.get_object()

    #     # ✅ Ensure booking is scheduled
    #     if booking.status != "Scheduled":
    #         return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

    #     # ✅ Ensure payment exists
    #     if not booking.payment_intent_id:
    #         return Response({'error': 'No PaymentIntent ID found. Ensure payment is completed.'}, status=400)

    #     # ✅ Ensure locksmith is correct
    #     locksmith = booking.locksmith_service.locksmith
    #     if locksmith.user != request.user:
    #         return Response({'error': 'Permission denied'}, status=403)

    #     # ✅ Ensure locksmith has Stripe account
    #     if not locksmith.stripe_account_id:
    #         return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

    #     try:
    #         # ✅ Retrieve PaymentIntent
    #         payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

    #         # ✅ If payment is already captured, transfer funds
    #         if payment_intent.status == "succeeded":
    #             total_price = booking.locksmith_service.total_price
    #             custom_price = booking.locksmith_service.custom_price

    #             # ✅ Deduction Calculation
    #             deduct_amount = total_price - custom_price
    #             transfer_amount = custom_price  # Only sending locksmith's custom price

    #             # ✅ Convert to cents
    #             transfer_amount_cents = int(transfer_amount * 100)

    #             # ✅ Transfer money to locksmith
    #             transfer = stripe.Transfer.create(
    #                 amount=transfer_amount_cents,
    #                 currency="aud",
    #                 destination=locksmith.stripe_account_id,
    #                 transfer_group=f"booking_{booking.id}"
    #             )

    #             # ✅ Mark booking as completed
    #             booking.status = "Completed"
    #             booking.payment_status = "paid"
    #             booking.save()

    #             return Response({
    #                 'status': 'Booking completed and payment transferred to locksmith',
    #                 'transfer_amount': transfer_amount,
    #                 'deducted_amount': deduct_amount
    #             })
                

    #         else:
    #             return Response({'error': f'Invalid PaymentIntent status: {payment_intent.status}'}, status=400)

    #     except stripe.error.StripeError as e:
    #         return Response({'error': str(e)}, status=400)
    
    
    # @action(detail=True, methods=['post'])
    # def complete_payment(self, request, pk=None):
    #     print(f"complete_payment called with pk={pk}")

    #     # Manual fetch to debug get_object issue
    #     try:
    #         booking = Booking.objects.get(pk=pk)
    #     except Booking.DoesNotExist:
    #         return Response({"error": "Booking not found."}, status=404)

    #     if not booking.stripe_session_id:
    #         return Response({"error": "Missing Stripe Session ID."}, status=400)

    #     try:
    #         # Retrieve Stripe Checkout Session
    #         session = stripe.checkout.Session.retrieve(booking.stripe_session_id)

    #         if session.payment_status == "paid":
    #             booking.payment_intent_id = session.payment_intent
    #             booking.payment_status = "paid"
    #             booking.status = "Scheduled"
    #             booking.save()

    #             locksmith = booking.locksmith_service.locksmith
    #             # call_locksmith(locksmith.contact_number, locksmith.user.get_full_name(), booking.id)

    #             return Response({
    #                 "status": "Payment confirmed and booking scheduled.",
    #                 "message": "Locksmith notified via automated call."
    #             })

    #         return Response({"error": "Payment is not completed yet."}, status=400)

    #     except stripe.error.StripeError as e:
    #         return Response({"error": str(e)}, status=400)
    
    # @action(detail=True, methods=['post'])
    # def complete_payment(self, request, pk=None):
    #     try:
    #         booking = Booking.objects.get(pk=pk)
    #     except Booking.DoesNotExist:
    #         return Response({"error": "Booking not found."}, status=404)

    #     if not booking.stripe_session_id:
    #         return Response({"error": "Missing Stripe Session ID."}, status=400)

    #     try:
    #         session = stripe.checkout.Session.retrieve(booking.stripe_session_id)

    #         if session.payment_status == "paid":
    #             booking.payment_intent_id = session.payment_intent
    #             booking.payment_status = "paid"
    #             booking.status = "Scheduled"
    #             booking.save()

    #             locksmith = booking.locksmith_service.locksmith
    #             customer = booking.customer

    #             # Locksmith SMS with customer details
    #             locksmith_message = (
    #                 f"Hello {locksmith.user.get_full_name()},\n"
    #                 f"You have a new booking (ID: {booking.id}) from customer {customer.get_full_name()}.\n"
    #                 f"Service: {booking.locksmith_service.admin_service.name}\n"
    #                 f"Customer Address: {booking.customer_address or 'N/A'}\n"
    #                 f"Customer Phone: {booking.customer_contact_number or customer.phone_number or 'N/A'}\n"
    #                 f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
    #                 f"Emergency Service: {'Yes' if booking.emergency else 'No'}\n"
    #                 f"Thank you."
    #             )
    #             send_sms(locksmith.contact_number, locksmith_message)


    #             # Customer SMS with locksmith details
    #             customer_message = (
    #                 f"Hello {customer.get_full_name()},\n"
    #                 f"Your payment for booking ID {booking.id} is successful.\n"
    #                 f"Locksmith: {locksmith.user.get_full_name()}\n"
    #                 f"Locksmith Phone: {locksmith.contact_number or 'N/A'}\n"
    #                 f"Service: {booking.locksmith_service.admin_service.name}\n"
    #                 f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
    #                 f"Thank you for choosing our service!"
    #             )
    #             send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

    #             return Response({
    #                 "status": "Payment confirmed and booking scheduled.",
    #                 "message": "SMS notifications sent to locksmith and customer."
    #             })

    #         return Response({"error": "Payment is not completed yet."}, status=400)

    #     except stripe.error.StripeError as e:
    #         return Response({"error": str(e)}, status=400)
    


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
                # customer_message = (
                #     f"Hello {customer.get_full_name()},\n"
                #     f"Your payment for the booking (ID: {booking.id}) is successful.\n"
                #     f"Please wait for the locksmith to approve your request.\n"
                #     f"You will be notified once it's approved or denied."
                # )
                # send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

                # ✅ Notify locksmith about the new booking
                # locksmith_message = (
                #     f"Hello {locksmith.user.get_full_name()},\n"
                #     f"You have a new booking (ID: {booking.id}) from customer {customer.get_full_name()}.\n"
                #     f"Service: {booking.locksmith_service.admin_service.name}\n"
                #     # f"Customer Address: {booking.customer_address or 'N/A'}\n"
                #     # f"Customer Phone: {booking.customer_contact_number or customer.phone_number or 'N/A'}\n"
                #     f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
                #     f"Emergency Service: {'Yes' if booking.emergency else 'No'}\n"
                #     f"Please approve or deny this booking."
                #     f"Thank you."
                # )
                # send_sms(locksmith.contact_number, locksmith_message)

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



    # @action(detail=True, methods=['post'])
    # def complete(self, request, pk=None):
    #     """
    #     Locksmith marks booking as completed and receives payment
    #     """
    #     booking = self.get_object()
    #     locksmith_service = booking.locksmith_service
    #     locksmith = locksmith_service.locksmith

    #     # Check booking status
    #     if booking.status != "Scheduled":
    #         return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

    #     # Check payment intent exists
    #     if not booking.payment_intent_id:
    #         return Response({'error': 'No PaymentIntent ID found. Ensure payment is completed.'}, status=400)

    #     # Check locksmith ownership
    #     if locksmith.user != request.user:
    #         return Response({'error': 'Permission denied'}, status=403)

    #     # Check locksmith Stripe account
    #     if not locksmith.stripe_account_id:
    #         return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

    #     try:
    #         # Retrieve PaymentIntent from Stripe
    #         payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

    #         if payment_intent.status == "succeeded":
    #             # Get admin settings
    #             admin_settings = AdminSettings.objects.first()
    #             commission_amount = admin_settings.commission_amount or Decimal("0.00")
    #             percentage = admin_settings.percentage or Decimal("0.00")

    #             # Calculate subtotal: base price + additional keys cost
    #             base_price = locksmith_service.custom_price or Decimal("0.00")
    #             number_of_keys = booking.number_of_keys or 0
    #             additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")
    #             keys_total = additional_key_price * Decimal(number_of_keys)

    #             subtotal = base_price + keys_total

    #             # Calculate percentage amount (commission)
    #             percentage_amount = (subtotal * percentage) / Decimal("100")

    #             # Calculate transfer amount = total_price - percentage_amount - commission_amount
    #             total_price = booking.total_price or Decimal("0.00")
    #             transfer_amount = total_price - percentage_amount - commission_amount

    #             if transfer_amount <= 0:
    #                 return Response({'error': 'Transfer amount is zero or negative after deductions.'}, status=400)

    #             # Convert to cents for Stripe
    #             transfer_amount_cents = int(transfer_amount * Decimal('100'))

    #             # Transfer payment to locksmith Stripe account
    #             stripe.Transfer.create(
    #                 amount=transfer_amount_cents,
    #                 currency="aud",
    #                 destination=locksmith.stripe_account_id,
    #                 transfer_group=f"booking_{booking.id}"
    #             )

    #             # Update booking status and payment_status
    #             booking.status = "Completed"
    #             booking.payment_status = "paid"
    #             booking.save()

    #             return Response({
    #                 'status': 'Booking completed and payment transferred to locksmith',
    #                 'total_price': str(total_price),
    #                 'subtotal': str(subtotal),
    #                 'percentage_amount': str(percentage_amount),
    #                 'commission_amount': str(commission_amount),
    #                 'transfer_amount': str(transfer_amount)
    #             })

    #         else:
    #             return Response({'error': f'Invalid PaymentIntent status: {payment_intent.status}'}, status=400)

    #     except stripe.error.StripeError as e:
    #         return Response({'error': str(e)}, status=400)
    
    
    # @action(detail=True, methods=['post'], permission_classes=[IsLocksmith])
    # def complete(self, request, pk=None):
    #     """
    #     Locksmith marks booking as completed and receives payment
    #     """
    #     booking = self.get_object()
    #     locksmith_service = booking.locksmith_service
    #     locksmith = locksmith_service.locksmith

    #     # Check if locksmith_status is APPROVED
    #     if booking.locksmith_status != "APPROVED":
    #         return Response(
    #             {'error': 'Booking must be approved by the locksmith before completion.'},
    #             status=400
    #         )

    #     # Check booking status
    #     if booking.status != "Scheduled":
    #         return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

    #     # Check payment intent exists
    #     if not booking.payment_intent_id:
    #         return Response({'error': 'No PaymentIntent ID found. Ensure payment is completed.'}, status=400)

    #     # Check locksmith ownership
    #     if locksmith.user != request.user:
    #         return Response({'error': 'Permission denied'}, status=403)

    #     # Check locksmith Stripe account
    #     if not locksmith.stripe_account_id:
    #         return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

    #     try:
    #         # Retrieve PaymentIntent from Stripe
    #         payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

    #         if payment_intent.status == "succeeded":
    #             # Get admin settings
    #             admin_settings = AdminSettings.objects.first()
    #             commission_amount = admin_settings.commission_amount or Decimal("0.00")
    #             percentage = admin_settings.percentage or Decimal("0.00")
    #             gst_percentage = admin_settings.gst_percentage or Decimal("0.00")

    #             # Calculate base price + additional keys
    #             base_price = locksmith_service.custom_price or Decimal("0.00")
    #             number_of_keys = booking.number_of_keys or 0
    #             additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")
    #             keys_total = additional_key_price * Decimal(number_of_keys)

    #             subtotal = base_price + keys_total

    #             # Platform % fee
    #             percentage_amount = (subtotal * percentage) / Decimal("100")

    #             # Platform income = fixed + %
    #             platform_income = commission_amount + percentage_amount

    #             # GST on platform income
    #             gst_amount = (platform_income * gst_percentage) / Decimal("100")

    #             # Total price (already stored in booking)
    #             total_price = booking.total_price or Decimal("0.00")

    #             # Now: Transfer only base_price + keys_total to locksmith (not platform fees, not GST)
    #             transfer_amount = base_price + keys_total

    #             if transfer_amount <= 0:
    #                 return Response({'error': 'Transfer amount is zero or negative after deductions.'}, status=400)

    #             # Convert to cents for Stripe
    #             transfer_amount_cents = int(transfer_amount * Decimal('100'))

    #             # Perform Stripe Transfer
    #             stripe.Transfer.create(
    #                 amount=transfer_amount_cents,
    #                 currency="aud",
    #                 destination=locksmith.stripe_account_id,
    #                 transfer_group=f"booking_{booking.id}"
    #             )

    #             # Update booking status and payment_status
    #             booking.status = "Completed"
    #             booking.payment_status = "paid"
    #             booking.save()

    #             # Return response with breakdown
    #             return Response({
    #                 'status': 'Booking completed and payment transferred to locksmith',
    #                 'total_price': str(total_price),
    #                 'locksmith_transfer_amount': str(transfer_amount),
    #                 'locksmith_charges': str(base_price),
    #                 'additional_key_charges': str(keys_total),
    #                 'platform_charges': str(commission_amount),
    #                 'service_charges': str(percentage_amount),
    #                 'gst': str(gst_amount),
    #                 'platform_income': str(platform_income),
    #             })

    #         else:
    #             return Response({'error': f'Invalid PaymentIntent status: {payment_intent.status}'}, status=400)

    #     except stripe.error.StripeError as e:
    #         return Response({'error': str(e)}, status=400)
    
    
    @action(detail=True, methods=['post'], permission_classes=[IsLocksmith])
    def complete(self, request, pk=None):
        """
        Locksmith marks booking as completed and receives payment.
        Uses source_transaction for safe transfer tied to Stripe charge.
        """
        booking = self.get_object()
        locksmith_service = booking.locksmith_service
        locksmith = locksmith_service.locksmith

        # Pre-checks
        if booking.locksmith_status != "APPROVED":
            return Response({'error': 'Booking must be approved before completion.'}, status=400)

        if booking.status != "Scheduled":
            return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

        if not booking.payment_intent_id:
            return Response({'error': 'No PaymentIntent ID found.'}, status=400)

        if locksmith.user != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        if not locksmith.stripe_account_id:
            return Response({'error': 'Locksmith does not have a Stripe account'}, status=400)

        try:
            # ✅ Safely retrieve the charge using PaymentIntent ID
            charges_list = stripe.Charge.list(payment_intent=booking.payment_intent_id)

            if not charges_list.data:
                return Response({'error': 'No charges found for this PaymentIntent.'}, status=400)

            charge_id = charges_list.data[0].id

            # Calculate transfer amount
            base_price = locksmith_service.custom_price or Decimal("0.00")
            number_of_keys = booking.number_of_keys or 0
            additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")
            keys_total = additional_key_price * Decimal(number_of_keys)
            transfer_amount = base_price + keys_total
            transfer_amount_cents = int(transfer_amount * Decimal("100"))

            if transfer_amount_cents <= 0:
                return Response({'error': 'Transfer amount must be greater than zero.'}, status=400)

            # ✅ Create the transfer using source_transaction
            transfer = stripe.Transfer.create(
                amount=transfer_amount_cents,
                currency="aud",
                destination=locksmith.stripe_account_id,
                source_transaction=charge_id,
                transfer_group=f"booking_{booking.id}"
            )

            # ✅ Update booking record
            booking.status = "Completed"
            booking.payment_status = "paid"
            booking.charge_id = charge_id
            booking.transfer_status = "completed"
            booking.locksmith_transfer_amount = transfer_amount
            booking.save()

            return Response({
                'status': 'Booking completed and transfer created successfully.',
                'total_price': str(booking.total_price),
                'locksmith_transfer_amount': str(transfer_amount),
                'locksmith_charges': str(base_price),
                'additional_key_charges': str(keys_total),
                'charge_id': charge_id,
                'transfer_status': booking.transfer_status
            })

        except stripe.error.StripeError as e:
            return Response({'error': f'Stripe error: {str(e)}'}, status=400)

        except Exception as e:
            return Response({'error': f'Unexpected error while completing booking: {str(e)}'}, status=500)







    # @action(detail=True, methods=['post'])
    # def complete(self, request, pk=None):
    #     """
    #     Booking completion confirmation by locksmith or customer.
    #     If both confirm, release payment to locksmith.
    #     """
    #     booking = self.get_object()
    #     user = request.user

    #     # Check valid booking state
    #     if booking.status != "Scheduled":
    #         return Response({'error': 'Booking is not in a valid state to be completed'}, status=400)

    #     # Determine who is confirming the completion
    #     if user.role == 'locksmith':
    #         if booking.locksmith_service.locksmith.user != user:
    #             return Response({'error': 'Permission denied'}, status=403)
    #         booking.is_locksmith_confirmed = True

    #     elif user.role == 'customer':
    #         if booking.customer != user:
    #             return Response({'error': 'Permission denied'}, status=403)
    #         booking.is_customer_confirmed = True

    #     else:
    #         return Response({'error': 'Invalid user role'}, status=403)

    #     booking.save()

    #     # Check if both have confirmed completion
    #     if booking.is_locksmith_confirmed and booking.is_customer_confirmed:
    #         result = self._release_payment(booking)
    #         if result.get("error"):
    #             return Response(result, status=400)

    #         return Response({
    #             'status': 'Booking completed and payment released to locksmith',
    #             **result
    #         })

    #     return Response({'status': 'Confirmation recorded. Waiting for other party to confirm.'})

    
    
    # def _release_payment(self, booking):
    #     """
    #     Handles deduction and transfers payment to locksmith via Stripe
    #     """
    #     try:
    #         locksmith_service = booking.locksmith_service
    #         locksmith = locksmith_service.locksmith

    #         if not booking.payment_intent_id:
    #             return {'error': 'No PaymentIntent ID found. Ensure payment is completed.'}

    #         if not locksmith.stripe_account_id:
    #             return {'error': 'Locksmith does not have a Stripe account'}

    #         payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)
    #         if payment_intent.status != "succeeded":
    #             return {'error': f'Invalid PaymentIntent status: {payment_intent.status}'}

    #         # Get admin settings
    #         admin_settings = AdminSettings.objects.first()
    #         commission_amount = admin_settings.commission_amount or Decimal("0.00")
    #         percentage = admin_settings.percentage or Decimal("0.00")

    #         # Subtotal = base + keys
    #         base_price = locksmith_service.custom_price or Decimal("0.00")
    #         number_of_keys = booking.number_of_keys or 0
    #         additional_key_price = locksmith_service.additional_key_price or Decimal("0.00")
    #         keys_total = additional_key_price * Decimal(number_of_keys)
    #         subtotal = base_price + keys_total

    #         # Calculate percentage deduction
    #         percentage_amount = (subtotal * percentage) / Decimal("100")

    #         total_price = booking.total_price or Decimal("0.00")
    #         transfer_amount = total_price - percentage_amount - commission_amount

    #         if transfer_amount <= 0:
    #             return {'error': 'Transfer amount is zero or negative after deductions.'}

    #         # Stripe transfer
    #         stripe.Transfer.create(
    #             amount=int(transfer_amount * 100),  # in cents
    #             currency="aud",
    #             destination=locksmith.stripe_account_id,
    #             transfer_group=f"booking_{booking.id}"
    #         )

    #         # Mark booking as completed
    #         booking.status = "Completed"
    #         booking.payment_status = "paid"
    #         booking.save()

    #         return {
    #             'total_price': str(total_price),
    #             'subtotal': str(subtotal),
    #             'percentage_amount': str(percentage_amount),
    #             'commission_amount': str(commission_amount),
    #             'transfer_amount': str(transfer_amount)
    #         }

    #     except stripe.error.StripeError as e:
    #         return {'error': str(e)}


    
    @action(detail=False, methods=["get"], permission_classes=[IsCustomer])
    def by_session(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"error": "Missing session_id"}, status=400)

        try:
            booking = Booking.objects.get(stripe_session_id=session_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)

        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    


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






# @csrf_exempt
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
#     webhook_secret = settings.STRIPE_WEBHOOK_SECRET

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#     except Exception as e:
#         print("❌ Webhook error:", str(e))
#         return HttpResponse(status=400)

#     print("✅ Event type:", event['type'])

#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']
#         session_id = session.get('id')
#         print("🔎 Session ID:", session_id)

#         try:
#             booking = Booking.objects.get(stripe_session_id=session_id)

#             if session.get('payment_status') == 'paid':
#                 booking.payment_intent_id = session.get('payment_intent')
#                 booking.payment_status = 'paid'
#                 booking.status = 'Scheduled'
#                 booking.save()

#                 customer = booking.customer
#                 locksmith = booking.locksmith_service.locksmith

#                 # Send SMS to customer
#                 customer_message = (
#                     f"Hello {customer.get_full_name()},\n"
#                     f"Your payment for the booking (ID: {booking.id}) is successful.\n"
#                     f"Please wait for the locksmith to approve your request.\n"
#                     f"You will be notified once it's approved or denied."
#                 )
#                 send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

#                 # Notify locksmith
#                 locksmith_message = (
#                     f"Hello {locksmith.user.get_full_name()},\n"
#                     f"You have a new booking (ID: {booking.id}) from customer {customer.get_full_name()}.\n"
#                     f"Service: {booking.locksmith_service.admin_service.name}\n"
#                     # f"Customer Address: {booking.customer_address or 'N/A'}\n"
#                     # f"Customer Phone: {booking.customer_contact_number or customer.phone_number or 'N/A'}\n"
#                     f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
#                     f"Emergency Service: {'Yes' if booking.emergency else 'No'}\n"
#                     f"Please approve or deny this booking."
#                 )
#                 send_sms(locksmith.contact_number, locksmith_message)

#                 print(f"✅ Booking {booking.id} updated and SMS sent.")

#         except Booking.DoesNotExist:
#             print(f"❌ Booking not found for session ID: {session_id}")
#             return JsonResponse({"error": "Booking not found"}, status=404)

#     return HttpResponse(status=200)



@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        print("❌ Webhook error:", str(e))
        return HttpResponse(status=400)

    print("✅ Event type:", event['type'])

    # ✅ Booking confirmation on successful payment
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        print("🔎 Session ID:", session_id)

        try:
            booking = Booking.objects.get(stripe_session_id=session_id)

            if session.get('payment_status') == 'paid':
                booking.payment_intent_id = session.get('payment_intent')
                booking.payment_status = 'paid'
                booking.status = 'Scheduled'
                booking.save()

                customer = booking.customer
                locksmith = booking.locksmith_service.locksmith

                # Send SMS to customer
                customer_message = (
                    f"Hello {customer.get_full_name()},\n"
                    f"Your payment for the booking (ID: {booking.id}) is successful.\n"
                    f"Please wait for the locksmith to approve your request.\n"
                    f"You will be notified once it's approved or denied."
                )
                send_sms(booking.customer_contact_number or customer.phone_number, customer_message)

                # Notify locksmith
                locksmith_message = (
                    f"Hello {locksmith.user.get_full_name()},\n"
                    f"You have a new booking (ID: {booking.id}) from customer {customer.get_full_name()}.\n"
                    f"Service: {booking.locksmith_service.admin_service.name}\n"
                    f"Scheduled Date: {booking.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Emergency Service: {'Yes' if booking.emergency else 'No'}\n"
                    f"Please approve or deny this booking."
                )
                send_sms(locksmith.contact_number, locksmith_message)

                print(f"✅ Booking {booking.id} updated and SMS sent.")

        except Booking.DoesNotExist:
            print(f"❌ Booking not found for session ID: {session_id}")
            return JsonResponse({"error": "Booking not found"}, status=404)

    # ✅ Update transfer status when funds are released
    elif event['type'] == 'transfer.paid':
        transfer = event['data']['object']
        charge_id = transfer.get('source_transaction')
        amount_cents = transfer.get('amount')

        print("🔄 Transfer Paid for Charge:", charge_id)

        try:
            booking = Booking.objects.get(charge_id=charge_id)

            booking.transfer_status = "completed"
            booking.locksmith_transfer_amount = Decimal(amount_cents) / 100
            booking.save()

            print(f"✅ Transfer recorded for booking {booking.id}")

        except Booking.DoesNotExist:
            print(f"⚠️ No booking found for charge ID: {charge_id}")

    return HttpResponse(status=200)




@api_view(['GET'])
def stripe_session_details(request):
    session_id = request.GET.get('session_id')
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return Response({
            "id": session.id,
            "payment_status": session.payment_status,
            "amount_total": session.amount_total
        })
    except stripe.error.StripeError as e:
        return Response({"error": str(e)}, status=400)



