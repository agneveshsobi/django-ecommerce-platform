from django.shortcuts import render
from django.http import JsonResponse
import json
import datetime
import paypalrestsdk
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect

from .models import * 
from .utils import cookieCart, cartData, guestOrder
from django.contrib.auth.models import User

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET,
})

def store(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    products = Product.objects.filter(category=None)
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/store.html', context)

def cart(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/cart.html', context)

def checkout(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/checkout.html', context)

def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    print('Action:', action)
    print('Product:', productId)

    customer = request.user.customer
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)

    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action == 'add':
        orderItem.quantity = (orderItem.quantity + 1)
    elif action == 'remove':
        orderItem.quantity = (orderItem.quantity - 1)

    orderItem.save()

    if orderItem.quantity <= 0:
        orderItem.delete()

    return JsonResponse('Item was added', safe=False)

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
    else:
        customer, order = guestOrder(request, data)

    total = float(data['form']['total'])
    order.transaction_id = transaction_id

    # Verify PayPal payment
    paypal_order_id = data.get('paypalOrderID')

    if paypal_order_id:
        try:
            payment = paypalrestsdk.Payment.find(paypal_order_id)
            if payment.state == 'approved':
                if total == order.get_cart_total:
                    order.complete = True
            else:
                return JsonResponse('Payment not approved by PayPal', safe=False, status=400)
        except Exception as e:
            return JsonResponse(f'PayPal error: {str(e)}', safe=False, status=400)
    else:
        return JsonResponse('No PayPal order ID provided', safe=False, status=400)

    order.save()

    if order.shipping == True:
        ShippingAddress.objects.create(
            customer=customer,
            order=order,
            address=data['shipping']['address'],
            city=data['shipping']['city'],
            state=data['shipping']['state'],
            zipcode=data['shipping']['zipcode'],
        )

    return JsonResponse('Payment submitted..', safe=False)


def loginPage(request):
    if request.user.is_authenticated:
        return redirect('store')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('store')
        else:
            return render(request, 'store/login.html', {'error': 'Username or password is incorrect'})

    return render(request, 'store/login.html')


def logoutUser(request):
    logout(request)
    return redirect('login')


def registerPage(request):
    if request.user.is_authenticated:
        return redirect('store')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 == password2:
            if User.objects.filter(username=username).exists():
                return render(request, 'store/register.html', {'error': 'Username already taken'})
            else:
                user = User.objects.create_user(username=username, email=email, password=password1)
                user.save()

                # ✅ Create Customer linked to this user
                Customer.objects.create(user=user, name=username, email=email)

                login(request, user)
                return redirect('store')
        else:
            return render(request, 'store/register.html', {'error': 'Passwords do not match'})

    return render(request, 'store/register.html')

def men(request):
    data = cartData(request)
    cartItems = data['cartItems']
    products = Product.objects.filter(category='men')
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/men.html', context)

def women(request):
    data = cartData(request)
    cartItems = data['cartItems']
    products = Product.objects.filter(category='women')
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/women.html', context)

def kids(request):
    data = cartData(request)
    cartItems = data['cartItems']
    products = Product.objects.filter(category='kids')
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/kids.html', context)