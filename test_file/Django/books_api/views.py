from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from .models import Author, Book
from .serializers import AuthorSerializer, BookSerializer

@api_view(['GET'])
def api_root(request, format=None):
    """
    API root endpoint providing links to main resources
    """
    return Response({
        'authors': reverse('author-list', request=request, format=format),
        'books': reverse('book-list', request=request, format=format),
    })

class AuthorViewSet(viewsets.ModelViewSet):
    """
    API endpoint for authors
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    """
    API endpoint for books
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filterset_fields = ['author', 'publication_date']
    search_fields = ['title', 'description', 'author__name']
    ordering_fields = ['publication_date', 'price']
    
    def get_queryset(self):
        """
        Optionally restricts the returned books by filtering against
        query parameters in the URL
        """
        queryset = Book.objects.all()
        # Example of filter by query param
        title = self.request.query_params.get('title', None)
        if title is not None:
            queryset = queryset.filter(title__icontains=title)
        return queryset