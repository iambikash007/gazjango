from django import forms
from gazjango.articles.models      import StoryConcept
from gazjango.accounts.models      import UserProfile


# note that this form should be saved manually (with commit=False)
class SubmitStoryConcept(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(SubmitStoryConcept, self).__init__(*args, **kwargs)
    
    class Meta:
        model = StoryConcept
        fields = ('name','due')
    
class ConceptSaveForm(forms.Form):
    name = forms.CharField(label = 'Concept',   widget=forms.TextInput(attrs={'size': 64}), required=True)
    notes= forms.CharField(label = 'Notes',     widget=forms.TextArea( attrs={'cols': 65}), required=True)
    due  = forms.CharField(label = 'Due Date',  widget=forms.TextInput(attrs={'size': 64})               )
    users= forms.MultipleChoiceField(
        label = 'Assignee',
        widget= admin_widgets.FilteredSelectMultiple('Users', False),
        required=False
    )