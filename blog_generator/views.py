import os
import json
import yt_dlp
import openai as oai
import assemblyai as aai
from pytube import YouTube
from blog_app import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


# Create your views here.
@login_required
def index(request):
    return render (request, 'index.html')


# get yt video title
def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title


# get audio file
def download_audio(link):

    output_path=settings.MEDIA_ROOT

    ydl_opts = {
        'format': 'bestaudio/best',  # Download the best available audio format
        'outtmpl': f'{output_path}/%(title)s.mp3',  # Output template
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            # Extract info and download
            info = ydl.extract_info(link, download=True)            

            # Construct the path to the downloaded file
            file_name = f"{info['title']}.mp3"
            new_file = os.path.join(output_path, file_name)

            return new_file

    except Exception as e:
        return JsonResponse({'error': f'{e}'}, status=400)


# get transcript
def get_transcription(link):

    audio_file = download_audio(link)
    aai.settings.api_key = "Your API Key" #AssemblyAI API used

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text


# use openAI to generate the blog
def generate_blog_from_transcript(transcript):

    oai.api_key = "Your API Key" #OpenAI API used

    prompt = f"Write a comprehensive blog article based on the following YouTube video transcript. Ensure the content is structured as a proper blog, not resembling a video transcript:\n\n{transcript}\n\nArticle:"
    
    response = oai.completions.create(
        model = "Your LLM",
        prompt = prompt,
        max_tokens = 1000
    )
    
    generated_content = response.choices[0].text.strip()
    return generated_content
    

@csrf_exempt
def generate_blog(request):

    if request.method == 'POST':

        try:
            data = json.loads(request.body)
            yt_link = data['link']

        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        title = yt_title(yt_link)

        transcript = get_transcription(yt_link)

        if not transcript:
            return JsonResponse({'error': " Failed to get transcript"}, status = 500)
        
        blog_content = generate_blog_from_transcript(transcript)
        
        if not blog_content:
            return JsonResponse({'error': " Failed to generate blog article"}, status = 500)

        # save blog article to database
        # return blog article as a response
        return JsonResponse({'content': blog_content})

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


def user_login(request):

    if request.method == 'POST':

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/')

        else:
            error_message = "Inavlid Login Credentials"
            return render (request, 'login.html', {'error_message' : error_message})

    return render (request, 'login.html')


def user_signup(request):

    if request.method == 'POST':

        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')

            except:
                error_message = "Error registering the user"
                return render (request, 'signup.html', {'error_message' : error_message})

        else:
            error_message = 'Passwords do not match'
            return render (request, 'signup.html', {'error_message' : error_message})

    return render (request, 'signup.html')


def user_logout(request):

    logout(request)
    return redirect('/')
