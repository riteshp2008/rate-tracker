from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RateProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'rate_providers',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='RateType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'rate_types',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Rate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rate_value', models.DecimalField(db_index=True, decimal_places=4, max_digits=10)),
                ('effective_date', models.DateField(db_index=True)),
                ('ingestion_timestamp', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rates', to='rates_app.rateprovider')),
                ('rate_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rates', to='rates_app.ratetype')),
            ],
            options={
                'db_table': 'rates',
                'ordering': ['-effective_date'],
                'unique_together': {('provider', 'rate_type', 'effective_date')},
            },
        ),
        migrations.CreateModel(
            name='RawIngestionRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(db_index=True, max_length=255)),
                ('raw_data', models.JSONField()),
                ('parsed_successfully', models.BooleanField(db_index=True, default=False)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('ingestion_timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('related_rates', models.ManyToManyField(blank=True, to='rates_app.rate')),
            ],
            options={
                'db_table': 'raw_ingestion_records',
                'ordering': ['-ingestion_timestamp'],
            },
        ),
        migrations.CreateModel(
            name='IngestionJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('source', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('failed', 'Failed'), ('partial', 'Partial')], db_index=True, default='pending', max_length=20)),
                ('total_records', models.IntegerField(default=0)),
                ('successful_records', models.IntegerField(default=0)),
                ('failed_records', models.IntegerField(default=0)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'ingestion_jobs',
                'ordering': ['-started_at'],
            },
        ),
        migrations.AddIndex(
            model_name='rate',
            index=models.Index(fields=['provider', 'rate_type', '-effective_date'], name='idx_provider_type_date'),
        ),
        migrations.AddIndex(
            model_name='rate',
            index=models.Index(fields=['provider', 'rate_type', '-ingestion_timestamp'], name='idx_provider_type_ingestion'),
        ),
        migrations.AddIndex(
            model_name='rate',
            index=models.Index(fields=['effective_date'], name='idx_effective_date'),
        ),
        migrations.AddIndex(
            model_name='rate',
            index=models.Index(fields=['ingestion_timestamp'], name='idx_ingestion_timestamp'),
        ),
        migrations.AddIndex(
            model_name='rawingestionrecord',
            index=models.Index(fields=['source', '-ingestion_timestamp'], name='idx_raw_source_ingestion'),
        ),
        migrations.AddIndex(
            model_name='rawingestionrecord',
            index=models.Index(fields=['parsed_successfully', '-ingestion_timestamp'], name='idx_raw_parse_success'),
        ),
        migrations.AddIndex(
            model_name='ingestionjob',
            index=models.Index(fields=['status', '-started_at'], name='idx_job_status_date'),
        ),
    ]
