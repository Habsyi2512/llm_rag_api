# Data Pengujian Tambahan Chatbot Disdukcapil

Dokumen ini berisi data pengujian tambahan untuk sistem chatbot layanan informasi publik kependudukan pada Disdukcapil Kepulauan Anambas. Data ini dapat digunakan untuk memperluas pengujian sistem RAG dan sistem tanpa RAG, terutama pada informasi biaya layanan, masa berlaku KTP-el, layanan Kartu Keluarga, serta simulasi pelacakan status dokumen.

## Tabel Data Pengujian Tambahan

| No | Pertanyaan Pengujian | Jawaban Referensi |
|---:|---|---|
| 25 | Apakah ada biaya yang harus dibayarkan untuk mengurus dokumen kependudukan, khususnya KTP? | Semua pelayanan pengurusan dokumen kependudukan di Disdukcapil TIDAK DIPUNGUT BIAYA. |
| 26 | Apakah KTP-el yang sudah habis masa berlakunya perlu diperpanjang kembali? | KTP-el yang diterbitkan sebelum tahun 2013 (Undang-Undang Nomor 24 Tahun 2013) secara otomatis berlaku seumur hidup dan tidak perlu diperpanjang. |
| 27 | Apa saja jenis penerbitan Kartu Keluarga yang dapat dilayani oleh Disdukcapil? | Penerbitan Kartu Keluarga terdiri atas penerbitan KK baru, penerbitan KK karena perubahan data, dan penerbitan KK karena hilang atau rusak. |
| 28 | Apa saja persyaratan penerbitan Kartu Keluarga baru bagi penduduk WNI? | Persyaratan penerbitan KK baru bagi penduduk WNI antara lain buku nikah atau kutipan akta perkawinan atau kutipan akta perceraian, surat keterangan pindah atau surat keterangan pindah datang bagi penduduk yang pindah, surat keterangan pindah luar negeri bagi WNI yang datang dari luar negeri, surat keterangan pengganti tanda identitas bagi penduduk rentan administrasi kependudukan, atau dokumen perubahan status kewarganegaraan jika diperlukan. |
| 29 | Apa persyaratan penerbitan Kartu Keluarga karena hilang atau rusak bagi penduduk WNI? | Persyaratan penerbitan KK karena hilang atau rusak bagi WNI adalah surat keterangan hilang dari kepolisian atau KK yang rusak, serta KTP-el. |
| 30 | Periksa status Kartu Keluarga saya dengan nomor 5803662818. | Berdasarkan data yang tersedia, dokumen Kartu Keluarga dengan nomor registrasi 5803662818 memiliki status Siap Diambil. Catatan: KTP bisa diambil di front office. Waktu selesai: 2026-05-18. |

---

# Prompt Pengujian RAG vs Tanpa RAG

Bagian ini digunakan sebagai acuan untuk melakukan pengujian tambahan terhadap sistem chatbot. Setiap pertanyaan dijalankan pada dua skenario, yaitu sistem berbasis RAG dan sistem tanpa RAG. Jawaban yang dihasilkan kemudian dibandingkan dengan jawaban referensi menggunakan metrik ROUGE-L.

## 1. Prompt Pengujian untuk Sistem RAG

Gunakan prompt berikut ketika chatbot menggunakan knowledge base dan hasil retrieval dari dokumen resmi atau database tracking.

```text
Anda adalah chatbot layanan informasi publik Dinas Kependudukan dan Pencatatan Sipil (Disdukcapil) Kepulauan Anambas.

Tugas Anda adalah menjawab pertanyaan pengguna berdasarkan konteks resmi yang diberikan oleh sistem. Konteks dapat berasal dari dokumen knowledge base atau data tracking dokumen yang tersimpan di database.

Gunakan hanya informasi yang tersedia pada konteks. Jangan menambahkan informasi di luar konteks. Jika informasi tidak ditemukan, jawab bahwa informasi tersebut tidak tersedia pada knowledge base atau data tracking sistem.

Konteks:
{KONTEKS_RAG_ATAU_DATA_TRACKING}

Pertanyaan pengguna:
{PERTANYAAN_UJI}

Berikan jawaban yang singkat, jelas, dan sesuai dengan data resmi.
```

## 2. Prompt Pengujian untuk Sistem Tanpa RAG

Gunakan prompt berikut ketika chatbot tidak menggunakan retrieval dokumen, knowledge base, atau database tracking.

```text
Anda adalah chatbot layanan informasi publik Dinas Kependudukan dan Pencatatan Sipil (Disdukcapil).

Tugas Anda adalah menjawab pertanyaan pengguna secara langsung tanpa menggunakan konteks dokumen eksternal, knowledge base, atau database tracking.

Pertanyaan pengguna:
{PERTANYAAN_UJI}

Berikan jawaban yang singkat dan jelas.
```

## 3. Format Pencatatan Hasil Pengujian

Gunakan tabel berikut untuk mencatat hasil pengujian sebelum dilakukan perhitungan ROUGE-L.

| No | Pertanyaan Uji | Jawaban Referensi | Jawaban Sistem RAG | Jawaban Sistem Tanpa RAG |
|---:|---|---|---|---|
| 25 |  |  |  |  |
| 26 |  |  |  |  |
| 27 |  |  |  |  |
| 28 |  |  |  |  |
| 29 |  |  |  |  |
| 30 |  |  |  |  |

## 4. Catatan Pengujian

1. Pertanyaan nomor 25 sampai 29 digunakan untuk menguji kemampuan chatbot dalam menjawab informasi berdasarkan knowledge base dokumen layanan kependudukan.
2. Pertanyaan nomor 30 digunakan untuk menguji kemampuan chatbot dalam membaca data tracking dokumen dari database lokal.
3. Pada sistem RAG, jawaban harus mengacu pada konteks hasil retrieval atau data tracking yang diberikan oleh sistem.
4. Pada sistem tanpa RAG, jawaban diberikan tanpa konteks dokumen dan tanpa akses database tracking.
5. Jawaban referensi digunakan sebagai pembanding utama untuk menghitung ROUGE-L Precision, Recall, dan F1-Score.
6. Pertanyaan tracking dokumen dapat dinilai secara khusus karena membutuhkan kecocokan nomor registrasi, jenis dokumen, status, catatan, dan waktu selesai.
