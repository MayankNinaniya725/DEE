from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('extractor', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadedpdf',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('ERROR', 'Error')], default='PENDING', max_length=20),
        ),
    ]
