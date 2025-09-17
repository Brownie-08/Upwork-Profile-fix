from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse
from notifications.models import Notification
from .models import TransportRequest, TransportBid, TransportContract

@receiver(post_save, sender=TransportBid)
def notify_bid_submitted(sender, instance, created, **kwargs):
    if created:
        job = instance.transport_job
        Notification.objects.create(
            user=job.client,
            title=f"New Bid on {job.get_service_type_display()} Job #{job.id}",
            message=f"Provider {instance.provider.username} submitted a bid of E{instance.amount}.",
            notification_type='bid_submitted',
            link=reverse('transport:job_detail', kwargs={'pk': job.id}),
            transport_request=job
        )

@receiver(post_save, sender=TransportBid)
def notify_bid_accepted(sender, instance, **kwargs):
    if instance.status == 'ACCEPTED':
        job = instance.transport_job
        # Notify provider
        Notification.objects.create(
            user=instance.provider,
            title=f"Bid Accepted for {job.get_service_type_display()} Job #{job.id}",
            message=f"Your bid of E{instance.amount} was accepted by {job.client.username}.",
            notification_type='bid_accepted',
            link=reverse('transport:job_detail', kwargs={'pk': job.id}),
            transport_request=job
        )
        # Notify other providers
        for bid in job.bids.exclude(id=instance.id).filter(status='PENDING'):
            Notification.objects.create(
                user=bid.provider,
                title=f"Bid Rejected for {job.get_service_type_display()} Job #{job.id}",
                message=f"Your bid was not accepted.",
                notification_type='bid_submitted',
                link=reverse('transport:job_detail', kwargs={'pk': job.id}),
                transport_request=job
            )

@receiver(post_save, sender=TransportContract)
def notify_contract_confirmed(sender, instance, **kwargs):
    if instance.status == 'CONFIRMED':
        job = instance.transport_job
        Notification.objects.create(
            user=job.client,
            title=f"Contract Confirmed for {job.get_service_type_display()} Job #{job.id}",
            message=f"Provider {instance.provider.username} confirmed the contract.",
            notification_type='contract_confirmed',
            link=reverse('transport:job_detail', kwargs={'pk': job.id}),
            transport_request=job
        )

@receiver(post_save, sender=TransportRequest)
def notify_job_status_updated(sender, instance, **kwargs):
    if hasattr(instance, '_previous_status') and instance._previous_status != instance.status:
        # Notify client
        Notification.objects.create(
            user=instance.client,
            title=f"Status Updated for {instance.get_service_type_display()} Job #{instance.id}",
            message=f"Your job status changed to {instance.get_status_display()}.",
            notification_type='job_status_updated',
            link=reverse('transport:job_detail', kwargs={'pk': instance.id}),
            transport_request=instance
        )
        # Notify provider (if assigned)
        if instance.provider:
            Notification.objects.create(
                user=instance.provider,
                title=f"Status Updated for {instance.get_service_type_display()} Job #{instance.id}",
                message=f"The job status changed to {instance.get_status_display()}.",
                notification_type='job_status_updated',
                link=reverse('transport:job_detail', kwargs={'pk': instance.id}),
                transport_request=instance
            )

@receiver(post_delete, sender=TransportRequest)
def notify_job_deleted(sender, instance, **kwargs):
    for bid in instance.bids.all():
        Notification.objects.create(
            user=bid.provider,
            title=f"{instance.get_service_type_display()} Job #{instance.id} Deleted",
            message=f"The job you bid on was deleted by {instance.client.username}.",
            notification_type='job_deleted',
            link=reverse('transport:transport_dashboard'),
            transport_request=None
        )
    Notification.objects.create(
        user=instance.client,
        title=f"{instance.get_service_type_display()} Job #{instance.id} Deleted",
        message="Your job was successfully deleted.",
        notification_type='job_deleted',
        link=reverse('transport:transport_dashboard'),
        transport_request=None
    )