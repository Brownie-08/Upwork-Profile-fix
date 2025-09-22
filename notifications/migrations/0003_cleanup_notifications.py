from django.db import migrations


def cleanup_notifications(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.filter(
        notification_type__in=[
            "taxi_bid",
            "taxi_bid_accepted",
            "taxi_contract_confirmed",
            "taxi_status_update",
            "delivery_bid",
            "delivery_bid_accepted",
            "delivery_status_update",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]
    operations = [migrations.RunPython(cleanup_notifications)]
