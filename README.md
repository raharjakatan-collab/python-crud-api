# Python CRUD API

REST API sederhana berbasis Python standard library, dibangun dan dideploy otomatis oleh pipeline Jenkins ke Docker. Data pesan disimpan sebagai file JSON di Docker named volume sehingga tetap ada saat container diganti.

## Endpoint

| Method | Path | Keterangan |
| --- | --- | --- |
| GET | `/` atau `/health` | Status layanan |
| GET | `/messages` | Daftar semua pesan |
| GET | `/messages/{index}` | Satu pesan berdasarkan index |
| POST | `/messages` | Buat pesan, body `{"message": "..."}`, maksimal 500 karakter |
| DELETE | `/messages?index={index}` | Hapus pesan berdasarkan index |

## Menjalankan lokal

```bash
docker build -t python-crud-api:manual .
docker volume create production-api-data
docker run -d --name production-api-container \
  -p 5000:5000 \
  -v production-api-data:/var/lib/backend_data \
  python-crud-api:manual
curl -i http://localhost:5000/health
```

## Pengujian

```bash
python -m unittest discover -s tests -v
```

Test memakai server di port acak dan file data sementara, sehingga tidak menyentuh data di volume.

## Pipeline Jenkins

`Jenkinsfile` menjalankan: checkout, syntax check, test otomatis, build image, deploy, dan health check.

- Image diberi tag `BUILD_NUMBER`, commit SHA pendek, dan `latest`.
- Deploy mengganti container `production-api-container` dan mempertahankan volume `production-api-data`.
- Container API dipasang ke network `jenkins-net`, sehingga Jenkins dapat menghubunginya lewat nama container. `localhost` di dalam container Jenkins tidak mengarah ke API.

`Dockerfile.jenkins` membangun image Jenkins dengan Docker CLI. Jenkins memakai image tersebut dan memasang Docker socket host, jadi konfigurasi ini hanya untuk mesin lab yang dipercaya.

## Rahasia

PAT GitHub disimpan sebagai Jenkins Credential dengan ID `github-pat-readonly`. Jangan menaruh PAT, ngrok authtoken, atau password di repository, URL, maupun screenshot.
