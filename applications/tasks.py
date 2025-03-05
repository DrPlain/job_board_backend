# applications/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_application_submitted_email(job_seeker_email, job_title):
    """
    Send an email to the job seeker when they submit an application.

    Args:
        job_seeker_email (str): The email address of the job seeker.
        job_title (str): The title of the job applied to.
    """
    subject = "Application Submitted Successfully"
    message = f"""
    Dear Applicant,

    Your application for the position "{job_title}" has been successfully submitted.
    We will notify you once the employer reviews your application.

    Best regards,
    Job Board Team
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [job_seeker_email],
        fail_silently=False,
    )

@shared_task
def send_application_accepted_email(job_seeker_email, job_title):
    """
    Send an email to the job seeker when their application is accepted.

    Args:
        job_seeker_email (str): The email address of the job seeker.
        job_title (str): The title of the job accepted for.
    """
    subject = "Congratulations! Your Application Has Been Accepted"
    message = f"""
    Dear Applicant,

    We are pleased to inform you that your application for the position "{job_title}"
    has been accepted by the employer. Please check your account for next steps.

    Congratulations and best of luck!
    Job Board Team
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [job_seeker_email],
        fail_silently=False,
    )