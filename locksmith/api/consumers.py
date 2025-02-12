import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ServiceRequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handles new WebSocket connection"""
        self.locksmith_id = self.scope['url_route']['kwargs']['locksmith_id']
        self.room_group_name = f'locksmith_{self.locksmith_id}'

        # Join Room Group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """Handles WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handles incoming messages from WebSocket clients"""
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_update',
                'message': data['message']
            }
        )

    async def send_update(self, event):
        """Sends messages to WebSocket clients"""
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))
