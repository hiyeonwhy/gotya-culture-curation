from django.db.models import Count, F, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import Comment, Post
from .permissions import IsOwnerOrReadOnly
from .serializers import CommentSerializer, PostDetailSerializer, PostListSerializer


class CommunityPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class PostListCreateView(generics.ListCreateAPIView):
    pagination_class = CommunityPagination

    def get_queryset(self):
        queryset = Post.objects.select_related("user").annotate(
            comment_count=Count("comments")
        ).order_by("-created_at")
        category = self.request.query_params.get("category", "").strip()
        search = self.request.query_params.get("search", "").strip()

        if category:
            queryset = queryset.filter(category=category)
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))
        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PostDetailSerializer
        return PostListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PostDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        comments = Comment.objects.select_related("user")
        return (
            Post.objects.select_related("user")
            .prefetch_related(Prefetch("comments", queryset=comments))
            .annotate(comment_count=Count("comments"))
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.query_params.get("track_view", "true").lower() != "false":
            Post.objects.filter(pk=instance.pk).update(view_count=F("view_count") + 1)
            instance.refresh_from_db(fields=["view_count"])
        serializer = self.get_serializer(instance)
        from rest_framework.response import Response

        return Response(serializer.data)


class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(post_id=self.kwargs["post_id"]).select_related("user")

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs["post_id"])
        serializer.save(user=self.request.user, post=post)


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.select_related("user", "post")
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
