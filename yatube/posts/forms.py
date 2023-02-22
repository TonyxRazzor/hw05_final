from django import forms
from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        label = {
            'text': ('Текст поста'),
            'group': ('Группа'),
            'image': ('Изображение'),
        }
        help_texts = {
            'text': ('Текст нового поста'),
            'group': ('Группа чей пост'),
            'image': ('Изображение')
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text', )

    def clean_text(self):
        data = self.cleaned_data['text']
        if len(data.lower()) == 0:
            raise forms.ValidationError('Это поле не может быть пустым')
        return data
