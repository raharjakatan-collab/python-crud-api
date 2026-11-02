# Laporan Praktikum CI/CD: Jenkins, GitHub, Docker, dan ngrok

Repository: https://github.com/raharjakatan-collab/python-crud-api

## 1. Perubahan dari kondisi awal

| Area | Sebelum | Sesudah |
| --- | --- | --- |
| `Jenkinsfile` | Checkout, build, deploy | Ditambah syntax check, test otomatis, tag image, volume, dan health check |
| `Dockerfile` | Memasang Flask yang tidak dipakai | Tanpa dependensi tambahan, `PYTHONUNBUFFERED=1`, `HEALTHCHECK` |
| `.dockerignore`, `README.md` | Kosong | Terisi |
| `app.py` | Body JSON bukan objek memutus koneksi | Menjawab HTTP 400, ditambah `GET /messages/{index}` |

## 2. Tugas C: persistensi data

Container bersifat sementara: lapisan tulisnya ikut hilang saat container dihapus. Named volume dikelola Docker secara terpisah dari container, sehingga isinya tetap ada walaupun container dihapus. Pipeline memasang volume yang sama ke `/var/lib/backend_data` pada setiap deploy, jadi container baru langsung membaca data milik container lama.

## 3. Tugas D: pengembangan

Empat pengembangan dikerjakan:

1. **Endpoint `GET /messages/{index}`.** Mengembalikan satu pesan; 404 jika index tidak ada, 400 jika bukan angka.
2. **Test otomatis.** `tests/test_api.py` berisi 11 test untuk health, validasi POST, GET, dan DELETE. Tahap ini berjalan sebelum build, sehingga kode yang gagal test tidak dideploy.
3. **Docker `HEALTHCHECK`.**
4. **Tag image berbasis commit SHA.** Selain `BUILD_NUMBER`, image diberi tag SHA pendek sehingga image yang berjalan dapat dilacak ke commit asalnya.

Perbandingan `HEALTHCHECK` dan health check Jenkins:

| | Docker `HEALTHCHECK` | Health check Jenkins |
| --- | --- | --- |
| Dijalankan oleh | Docker, dari dalam container | Pipeline, dari luar container |
| Waktu | Terus-menerus selama container hidup | Sekali, saat deploy |
| Yang dibuktikan | Proses menjawab dari dalam container | API dapat dijangkau lewat jaringan |
| Hasil gagal | Status `unhealthy`, container tetap jalan | Build gagal |

Keduanya saling melengkapi. Image `python:3.11-slim` tidak berisi curl, jadi `HEALTHCHECK` memakai `urllib` dari Python.

## 4. Kegagalan yang ditemukan dan penyelesaiannya

**Health check dari panduan tidak cocok untuk Jenkins di dalam container.** `curl http://localhost:5000/health` berjalan di dalam container Jenkins, dan di sana `localhost` adalah container Jenkins sendiri, bukan host tempat port 5000 dipublikasikan. Solusinya, container API dipasang ke network `jenkins-net` dan dipanggil lewat namanya, `http://production-api-container:5000/health`.

**Health check langsung sesudah deploy terlalu cepat.** Saat uji, percobaan pertama gagal dengan `curl: (7)` karena API belum siap, lalu berhasil pada percobaan kedua. `sleep 3` diganti dengan pengulangan hingga 10 kali.

**Akses Docker socket ditolak.** Setelah Docker Desktop dimulai ulang, `docker version` dari container Jenkins gagal dengan `permission denied`, karena socket dimiliki `root:root` dengan mode 660 sementara Jenkins berjalan sebagai user `jenkins`. Solusinya memberi akses socket ke grup `jenkins`:

```bash
docker exec -u root jenkins-server chgrp jenkins /var/run/docker.sock
```

Perubahan ini hilang setiap Docker Desktop dimulai ulang, jadi perintah perlu dijalankan lagi.

## 5. Hasil pengujian

Setiap perintah `sh` dari `Jenkinsfile` dijalankan di container sementara berbasis image Jenkins yang sama, dengan nama container, volume, dan port uji. Hasil ini bukan dari build Jenkins; screenshot build tetap harus diambil dari Jenkins.

| Kasus uji | Hasil |
| --- | --- |
| Test otomatis | 11 test lulus |
| `GET /health` | 200, status active |
| `GET /messages` kosong | `{"messages": [], "total": 0}` |
| `POST /messages` | 201 |
| `POST` pesan kosong | 400 |
| `POST` body bukan objek JSON | 400 |
| `GET /messages/1` | 200 |
| `DELETE /messages?index=0` | 200 |
| `DELETE /messages?index=999` | 404 |
| Status `HEALTHCHECK` Docker | `healthy` |
| Persistensi | 2 pesan tetap ada setelah container diganti |
| Tag image | Nomor build, SHA, dan `latest` terbentuk |

## 6. Jawaban pertanyaan analisis

**Urutan peristiwa dari `git push` hingga container baru berjalan.** Commit masuk ke GitHub, lalu GitHub mengirim event push ke URL ngrok. ngrok meneruskannya ke Jenkins di port 8080 pada path `/github-webhook/`. Jenkins mencocokkan URL repository dengan job, mengambil kode memakai credential, lalu membaca `Jenkinsfile`. Pipeline menjalankan syntax check, test, dan build image. Container lama dihentikan dan dihapus, container baru dijalankan dengan volume yang sama, lalu health check memastikan API menjawab.

**Perbedaan PAT, webhook secret, dan ngrok authtoken.** PAT membuktikan identitas Jenkins saat mengakses repository GitHub. Webhook secret dipakai Jenkins untuk memastikan payload webhook benar-benar berasal dari GitHub, lewat tanda tangan HMAC. ngrok authtoken menghubungkan agent ngrok di komputer ke akun ngrok. Ketiganya berbeda arah dan tidak dapat saling menggantikan.

**Mengapa PAT read-only cukup untuk checkout tetapi tidak untuk push.** Checkout hanya membaca isi repository, dan itulah yang diizinkan `Contents: Read-only`. Push mengubah repository sehingga butuh `Contents: Read and write`, dan GitHub menolaknya. Hak minimum juga membatasi dampak jika token bocor.

**Risiko memasang Docker socket host ke container Jenkins.** Siapa pun yang mengakses socket dapat mengendalikan Docker daemon: menjalankan container privileged, memasang filesystem host, membaca volume lain, dan menghapus container. Artinya setara akses root ke host, sehingga job atau `Jenkinsfile` berbahaya dapat mengambil alih mesin.

**Mengapa URL ngrok yang berubah memutus webhook.** Payload URL di GitHub tersimpan statis. Jika URL ngrok berubah saat agent dimulai ulang, GitHub tetap mengirim ke alamat lama yang sudah tidak terhubung ke Jenkins, sehingga build tidak terpicu. Payload URL harus diperbarui, atau memakai domain tetap.

**Mengapa data named volume bertahan setelah container dihapus.** Volume disimpan di area Docker sendiri, di luar lapisan tulis container, dan punya lifecycle terpisah. `docker rm` tidak menghapus named volume; hanya `docker volume rm` yang melakukannya.

**Perbedaan CI dan CD pada pipeline ini.** CI memvalidasi perubahan: checkout, syntax check, test, dan build image. CD mengirim hasilnya ke lingkungan berjalan: deploy container dan health check.

**Jika deploy sukses tetapi health check gagal.** Pipeline harus ditandai gagal. Periksa `docker ps -a` dan `docker logs production-api-container`, lalu kembalikan layanan ke image sebelumnya memakai tag build lama, misalnya `python-crud-api:<nomor-build>`, dengan volume yang sama. Setelah itu perbaiki penyebabnya lewat commit baru.

## 7. Lampiran bukti

Bagian ini diisi setelah pipeline berjalan di Jenkins:

- [ ] Screenshot job Jenkins dengan build sukses
- [ ] Console Output: checkout, syntax check, build image, deploy, health check
- [ ] Screenshot GitHub Webhook Recent Deliveries
- [ ] Bukti build terpicu otomatis oleh push
- [ ] Output `curl` health dan CRUD dari `localhost:5000`
- [ ] Bukti pesan tetap ada setelah redeploy lewat Jenkins
