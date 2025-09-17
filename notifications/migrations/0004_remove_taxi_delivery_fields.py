from django.db import migrations


def migrate_table(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE notifications_notification_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                is_read BOOLEAN NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                link VARCHAR(200) NULL,
                project_id BIGINT NULL,
                transaction_id BIGINT NULL,
                chat_message_id BIGINT NULL,
                user_id INTEGER NOT NULL,
                transport_request_id INTEGER NULL
            );
        """
        )
        cursor.execute(
            """
            INSERT INTO notifications_notification_new (
                id, title, message, created_at, is_read, notification_type, link,
                project_id, transaction_id, chat_message_id, user_id, transport_request_id
            )
            SELECT
                id, title, message, created_at, is_read, notification_type, link,
                project_id, transaction_id, chat_message_id, user_id, transport_request_id
            FROM notifications_notification;
        """
        )
        cursor.execute("DROP TABLE notifications_notification;")
        cursor.execute(
            "ALTER TABLE notifications_notification_new RENAME TO notifications_notification;"
        )


class Migration(migrations.Migration):
    dependencies = [("notifications", "0003_cleanup_notifications")]
    operations = [migrations.RunPython(migrate_table)]
