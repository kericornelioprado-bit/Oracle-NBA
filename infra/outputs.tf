output "bucket_name" {
  value = google_storage_bucket.nba_data_lake.name
}

output "bucket_url" {
  value = google_storage_bucket.nba_data_lake.url
}
