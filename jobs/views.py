from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView
from django.contrib import messages
from businesses.views import BusinessRequiredMixin
from businesses.models import BusinessProfile
from .models import JobPosting
from .forms import JobPostingForm

class JobPostView(BusinessRequiredMixin, View):
    """
    Form view for business owners to post a new shift.
    Sets status as active by default.
    """
    template_name = 'businesses/post-job.html'

    def get(self, request):
        profile = get_object_or_404(BusinessProfile, user=request.user)
        form = JobPostingForm()
        return render(request, self.template_name, {
            'form': form,
            'profile': profile
        })

    def post(self, request):
        profile = get_object_or_404(BusinessProfile, user=request.user)
        form = JobPostingForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.business = profile
            job.status = 'active'  # Make immediately active
            job.save()
            messages.success(request, f"Shift '{job.title}' posted successfully!")
            return redirect('job_management')
        
        return render(request, self.template_name, {
            'form': form,
            'profile': profile
        })


class JobManageView(BusinessRequiredMixin, ListView):
    """
    Lists all shifts posted by the authenticated business owner.
    """
    template_name = 'businesses/manage-jobs.html'
    context_object_name = 'jobs'

    def get_queryset(self):
        profile = get_object_or_404(BusinessProfile, user=self.request.user)
        return JobPosting.objects.filter(business=profile).order_by('-created_at')
