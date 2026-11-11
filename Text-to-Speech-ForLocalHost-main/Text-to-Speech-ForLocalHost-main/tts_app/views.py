import os
import time
import uuid
import asyncio
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import edge_tts

def index(request):
    """
    Renders the main page of the application.
    """
    return render(request, 'tts_app/index.html')

async def generate_tts(request):
    """
    Asynchronous view to handle text-to-speech generation using edge-tts.
    Accepts POST requests via AJAX.
    """
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        voice = request.POST.get('voice', 'en-US-AriaNeural')
        speed = request.POST.get('speed', 'normal')

        if not text:
            return JsonResponse({'error': 'Text is required.'}, status=400)

        # Map speed strings to edge-tts rate format
        rate_map = {
            'slow': '-20%',
            'normal': '+0%',
            'fast': '+20%'
        }
        rate = rate_map.get(speed, '+0%')

        # Generate unique filename
        filename = f"tts_{uuid.uuid4().hex[:8]}_{int(time.time())}.mp3"
        filepath = os.path.join(settings.MEDIA_ROOT, 'tts_audio', filename)

        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(filepath)
            
            audio_url = f"{settings.MEDIA_URL}tts_audio/{filename}"
            return JsonResponse({
                'success': True,
                'audio_url': audio_url,
                'filename': filename
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)
