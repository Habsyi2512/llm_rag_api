# Daftar Pertanyaan Pengujian Tambahan Chatbot Disdukcapil

Dokumen ini berisi 14 pertanyaan pengujian tambahan untuk memperluas dataset evaluasi chatbot layanan informasi publik kependudukan berbasis RAG. Pertanyaan dirancang agar mencakup variasi layanan administrasi kependudukan selain pertanyaan standar tentang KTP, sehingga pengujian dapat menilai kemampuan chatbot dalam menjawab kasus layanan yang lebih beragam.

## Tabel Pertanyaan Pengujian Tambahan

| No | Pertanyaan Pengujian | Jawaban Referensi |
|---:|---|---|
| 11 | Saya ingin pindah domisili ke daerah lain. Dokumen apa yang digunakan untuk menerangkan perpindahan penduduk WNI? | Dokumen yang digunakan adalah SKPWNI atau Surat Keterangan Pindah Warga Negara Indonesia, yaitu dokumen kependudukan yang menerangkan perpindahan penduduk ke daerah domisili yang baru. |
| 12 | Berapa lama proses pembuatan SKPWNI di Disdukcapil Kepulauan Anambas setelah semua persyaratan diterima? | Pembuatan SKPWNI diproses paling lama dalam waktu 2 hari kerja setelah semua persyaratan diterima dan tidak dikenakan biaya. |
| 13 | Jika penduduk pindah datang ke daerah baru, apakah perpindahan tersebut dapat berkaitan dengan penerbitan Kartu Keluarga baru? | Ya, penerbitan KK baru dapat dilakukan untuk penduduk yang pindah datang, termasuk penduduk yang tidak diikuti kepala keluarga atau WNI yang datang dari luar wilayah Indonesia karena pindah. |
| 14 | Jika penduduk pindah ke alamat rumah yang bukan miliknya, dokumen tambahan apa yang perlu disiapkan? | Diperlukan surat pernyataan di atas materai tidak keberatan penggunaan alamat dalam dokumen kependudukan dari pemilik rumah. |
| 15 | Apa fungsi layanan Kartu Identitas Anak dalam administrasi kependudukan? | Kartu Identitas Anak atau KIA merupakan identitas resmi anak sebagai bukti diri bagi anak yang berusia kurang dari 17 tahun dan belum menikah. |
| 16 | Berapa lama proses penerbitan Kartu Identitas Anak di Disdukcapil Kepulauan Anambas? | Penerbitan Kartu Identitas Anak diproses paling lama dalam waktu 2 hari kerja setelah semua persyaratan diterima dan tidak dikenakan biaya. |
| 17 | Apa saja persyaratan utama pencatatan kelahiran WNI di wilayah Indonesia? | Persyaratan pencatatan kelahiran WNI meliputi surat keterangan kelahiran, buku nikah atau kutipan akta perkawinan atau bukti lain yang sah, Kartu Keluarga, dan KTP-el. |
| 18 | Apakah KTP-el ibu tetap dipersyaratkan dalam pencatatan kelahiran apabila ibu kandung belum berusia 17 tahun dan belum kawin? | Tidak. KTP-el tidak dipersyaratkan bagi ibu kandung yang belum berusia 17 tahun dengan status belum kawin. |
| 19 | Bagaimana pencatatan akta kelahiran anak jika orang tua tidak memiliki buku nikah atau kutipan akta perkawinan dan status hubungan dalam KK tidak menunjukkan suami istri? | Anak dicatat dalam register akta kelahiran dan kutipan akta kelahiran sebagai anak seorang ibu. |
| 20 | Bagaimana pencatatan akta kelahiran jika orang tua tidak memiliki buku nikah, tetapi status hubungan dalam KK menunjukkan suami istri? | Anak dicatat sebagai anak ayah dan ibu dengan tambahan frasa bahwa perkawinannya belum tercatat sesuai ketentuan peraturan perundang-undangan. |
| 21 | Jika terjadi perceraian, apakah data Kartu Keluarga dapat diperbarui karena peristiwa tersebut? | Ya. Perceraian termasuk peristiwa penting yang dapat menjadi dasar penerbitan KK karena perubahan data sesuai ketentuan administrasi kependudukan. |
| 22 | Apa fungsi layanan penerbitan Akta Perceraian di Disdukcapil? | Akta Perceraian digunakan untuk mencatat perceraian yang telah diputuskan oleh pengadilan dan berkekuatan hukum tetap. |
| 23 | Jika kepala keluarga meninggal dunia, dokumen apa yang dapat menjadi syarat tambahan untuk penerbitan KK baru karena penggantian kepala keluarga? | Penerbitan KK baru karena penggantian kepala keluarga dapat dilengkapi dengan syarat tambahan berupa akta kematian. |
| 24 | Apakah dokumen kependudukan yang sudah menggunakan tanda tangan elektronik, QR code, atau barcode masih perlu dilegalisir? | Tidak. Dokumen kependudukan dengan format digital berupa QR code atau barcode dan sudah ditandatangani secara elektronik tidak memerlukan legalisir. |

---

# Prompt Pengujian RAG vs Tanpa RAG

Bagian ini dapat digunakan sebagai acuan untuk melakukan pengujian perbandingan antara chatbot berbasis RAG dan chatbot tanpa RAG. Setiap pertanyaan pada tabel di atas dijalankan dua kali, yaitu satu kali menggunakan sistem RAG dan satu kali menggunakan sistem tanpa RAG. Hasil jawaban dari kedua sistem kemudian dibandingkan dengan jawaban referensi menggunakan metrik ROUGE-L.

## 1. Prompt Pengujian untuk Sistem RAG

Gunakan prompt berikut ketika sistem menggunakan dokumen knowledge base dan hasil retrieval dari vector database.

```text
Anda adalah chatbot layanan informasi publik Dinas Kependudukan dan Pencatatan Sipil (Disdukcapil) Kepulauan Anambas.

Tugas Anda adalah menjawab pertanyaan pengguna berdasarkan konteks dokumen resmi yang diberikan oleh sistem retrieval. Gunakan hanya informasi yang tersedia pada konteks. Jangan menambahkan informasi di luar konteks. Jika informasi tidak ditemukan pada konteks, jawab bahwa informasi tersebut tidak tersedia pada dokumen knowledge base.

Konteks hasil retrieval:
{KONTEKS_RAG}

Pertanyaan pengguna:
{PERTANYAAN_UJI}

Berikan jawaban yang singkat, jelas, dan sesuai dengan dokumen resmi.
```

## 2. Prompt Pengujian untuk Sistem Tanpa RAG

Gunakan prompt berikut ketika sistem tidak menggunakan retrieval dokumen atau knowledge base.

```text
Anda adalah chatbot layanan informasi publik Dinas Kependudukan dan Pencatatan Sipil (Disdukcapil).

Tugas Anda adalah menjawab pertanyaan pengguna secara langsung tanpa menggunakan konteks dokumen eksternal atau hasil retrieval dari knowledge base.

Pertanyaan pengguna:
{PERTANYAAN_UJI}

Berikan jawaban yang singkat dan jelas.
```

## 3. Format Pencatatan Hasil Pengujian

Gunakan format berikut untuk mencatat hasil jawaban dari kedua sistem sebelum dilakukan perhitungan ROUGE-L.

| No | Pertanyaan Uji | Jawaban Referensi | Jawaban Sistem RAG | Jawaban Sistem Tanpa RAG |
|---:|---|---|---|---|
| 11 |  |  |  |  |
| 12 |  |  |  |  |
| 13 |  |  |  |  |
| 14 |  |  |  |  |
| 15 |  |  |  |  |
| 16 |  |  |  |  |
| 17 |  |  |  |  |
| 18 |  |  |  |  |
| 19 |  |  |  |  |
| 20 |  |  |  |  |
| 21 |  |  |  |  |
| 22 |  |  |  |  |
| 23 |  |  |  |  |
| 24 |  |  |  |  |

## 4. Catatan Pengujian

1. Pertanyaan yang sama harus diberikan kepada sistem RAG dan sistem tanpa RAG.
2. Jawaban sistem RAG harus menggunakan konteks dari dokumen knowledge base.
3. Jawaban sistem tanpa RAG tidak boleh menggunakan dokumen knowledge base.
4. Jawaban referensi digunakan sebagai pembanding utama dalam perhitungan ROUGE-L.
5. Hasil pengujian dapat dihitung menggunakan nilai Precision, Recall, dan F1-Score berdasarkan Longest Common Subsequence (LCS).
6. Semakin tinggi nilai ROUGE-L, semakin tinggi tingkat kemiripan jawaban sistem terhadap jawaban referensi.
