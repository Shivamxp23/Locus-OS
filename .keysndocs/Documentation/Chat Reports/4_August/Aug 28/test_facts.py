import sys; sys.path.insert(0, '.')
from core.learning.user_profile import _extract_user_facts
facts = _extract_user_facts([
    {'role': 'user', 'content': 'I prefer using Python over JavaScript for backend work'},
    {'role': 'user', 'content': 'Hi'},
    {'role': 'user', 'content': "I am a software engineer at Google working on AI systems"},
])
print(f'Facts extracted: {facts}')
