from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.urls import reverse
from django.views.decorators.cache import never_cache

# Create your views here.
from .models import UserRegistration
from .serializers import RegistrationSerializer
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def register_user(request):
    serializer = RegistrationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def list_users(request):
    users = UserRegistration.objects.all()
    serializer = RegistrationSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET', 'PUT', 'DELETE'])
def user_detail(request, pk):
    try:
        user = UserRegistration.objects.get(pk=pk)
    except UserRegistration.DoesNotExist:
        return Response({"error": "Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = RegistrationSerializer(user)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = RegistrationSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    elif request.method == 'DELETE':
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
def login_view(request):
    # GET: if already logged in, go to users list
    if request.method == "GET":
        if request.session.get("user_id"):
            return redirect('registration:users_html')
        return render(request, 'registrations/login.html')

    # POST: authenticate by email/password
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')

    if not email or not password:
        messages.error(request, "Enter both email and password.")
        return render(request, 'registrations/login.html', {'email': email})

    try:
        user = UserRegistration.objects.get(email=email)
    except UserRegistration.DoesNotExist:
        messages.error(request, "Invalid credentials.")
        return render(request, 'registrations/login.html', {'email': email})

    # If password is already hashed, check it
    if check_password(password, user.password):
        request.session['user_id'] = user.id
        request.session['user_name'] = f"{user.first_name} {user.last_name}"
        return redirect('registration:users_html')

    # If stored as plain text, hash it once and log in
    if user.password == password:
        user.password = make_password(password)
        user.save(update_fields=['password'])
        request.session['user_id'] = user.id
        request.session['user_name'] = f"{user.first_name} {user.last_name}"
        return redirect('registration:users_html')

    messages.error(request, "Invalid credentials.")
    return render(request, 'registrations/login.html', {'email': email})

def logout_view(request):
    request.session.flush()
    # Redirect to login page; avoid serving cached protected pages
    return redirect('registration:login_html')

# Simple decorator to require a session login
def login_required_view(fn):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect(f"{reverse('registration:login_html')}?next={request.path}")
        resp = fn(request, *args, **kwargs)
        # Add no-cache headers so Back button doesn't show stale protected pages
        try:
            resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp["Pragma"] = "no-cache"
            resp["Expires"] = "0"
        except Exception:
            pass
        return resp
    wrapper.__name__ = fn.__name__
    return wrapper

@never_cache
@login_required_view
def users_html(request):
    users = UserRegistration.objects.all().order_by('id')
    return render(request, 'registrations/users_lists.html', {
        'users': users,
        'current_user': request.session.get('user_name')
    })

# Also prevent caching of login page itself
login_view = never_cache(login_view)
