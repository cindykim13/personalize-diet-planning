# Hệ thống Khuyến nghị Kế hoạch Dinh dưỡng Cá nhân hóa 
> **Dự án**: DietPlanning - Nền tảng xây dựng thực đơn tối ưu hóa bằng Trí tuệ Nhân tạo (AI) và Quy hoạch Tuyến tính.  
> **Kiến trúc**: Monolithic (Django MVT) kết hợp Data Science Pipeline.  
> **Nền tảng**: Python (Django), TensorFlow/Keras, PuLP, PostgreSQL.  

---

## 1. Tóm tắt (Abstract)

Một hệ thống phần mềm thông minh được thiết kế nhằm mục đích cung cấp các kế hoạch ăn uống (Meal Plan) mang tính cá nhân hóa cao. Hệ thống kết hợp các mô hình học máy (Machine Learning) để phân cụm và dự đoán đặc trưng món ăn, đồng thời ứng dụng thuật toán Tối ưu hóa Quy hoạch tuyến tính (Linear Programming Optimization) để tính toán khẩu phần ăn đáp ứng chính xác nhu cầu dinh dưỡng (Calories, Macros) của từng cá nhân.

---

## 2. Giới thiệu tổng quan và Đặt vấn đề (Introduction & Problem Statement)
Hiện nay, việc xây dựng một thực đơn dinh dưỡng khoa học gặp nhiều rào cản do mỗi cá nhân có một chỉ số sinh lý (BMR, TDEE), mục tiêu (giảm cân, duy trì, tăng cơ) và sở thích ăn uống khác nhau.
**DietPlanning** giải quyết bài toán này bằng cách:
- Số hóa và phân loại hàng ngàn công thức nấu ăn.
- Tự động tính toán nhu cầu năng lượng dựa trên hồ sơ sinh trắc học của người dùng (Tuổi, Giới tính, Cân nặng, Chiều cao, Mức độ vận động).
- Sử dụng thuật toán tối ưu hóa toán học để chọn lọc sự kết hợp hoàn hảo giữa các món ăn (Bữa sáng, Trưa, Tối) sao cho tổng lượng dinh dưỡng bám sát mục tiêu đề ra nhưng vẫn đảm bảo sự đa dạng và cấu trúc bữa ăn hợp lý.

---

## 3. Mục tiêu và Phạm vi Hệ thống (Objectives and Scope)
Hệ thống xoay quanh chu trình: Thu thập thông tin -> Dự đoán AI -> Tối ưu hóa tổ hợp món ăn -> Xuất bản thực đơn.

**Phạm vi chức năng bao gồm 4 module chính:**
1. **Hồ sơ Người dùng (User Profiling):** Thu thập dữ liệu sinh trắc học, chế độ ăn (Keto, Vegan, v.v.), dị ứng, tính toán BMR và Macro mục tiêu.
2. **Mô hình Trí tuệ Nhân tạo (AI Prediction Engine):** Sử dụng mạng nếp gấp (Keras Neural Network) và RobustScaler để phân loại các công thức nấu ăn mới vào các cụm (Cluster) dinh dưỡng tương ứng.
3. **Công cụ Tối ưu hóa (Optimization Engine):** Sử dụng thư viện `PuLP` giải bài toán quy hoạch tuyến tính (Linear Programming). Cân bằng giữa các hàm mục tiêu (ưu tiên độ chính xác của lượng Protein) và các ràng buộc cấu trúc (Ví dụ: Bữa trưa phải có 1 Món chính + 1 Món phụ).
4. **Tích hợp Dịch vụ Mở rộng (External Integrations):** Đồng bộ hình ảnh món ăn trực quan thông qua API của TheMealDB / Unsplash.

---

## 4. Kiến trúc Hệ thống (System Architecture)
Dự án được xây dựng theo mô hình MVT (Model-View-Template) của Django kết hợp với một Data Science Pipeline độc lập.

### 4.1. Kiến trúc luồng dữ liệu (Data Pipeline)
- **Data Exploration & Processing:** Dữ liệu thô được làm sạch, xử lý và chuẩn hóa qua các tài liệu Jupyter Notebook (`01_Data_Exploration.ipynb`, `02_Data_Processing.ipynb`).
- **Model Training:** Huấn luyện mô hình phân loại cụm dinh dưỡng (`03_Model_Training.ipynb`) và xuất ra các Model Artifacts (`.keras`, `.joblib`).

### 4.2. Kiến trúc Phần mềm (Software Components)
- **`core/`**: Thư mục gốc chứa các cấu hình quan trọng của dự án Django (Settings, Routing, Database configs).
- **`planner/`**: Ứng dụng chính (App) chứa toàn bộ logic hệ thống:
  - **`models.py`**: Định nghĩa cấu trúc Database cho `Recipe`, `UserProfile`, `PlanGenerationEvent` và `GeneratedPlan`.
  - **`ai_service.py`**: Singleton Service quản lý AI. Áp dụng cơ chế **Lazy Loading** (tải trễ) để nạp mô hình vào RAM chỉ khi có yêu cầu đầu tiên, giúp khắc phục triệt để lỗi treo server lúc startup.
  - **`optimization_service.py`**: Trái tim của hệ thống. Chứa các thuật toán giải bài toán tối ưu tổ hợp bữa ăn `create_single_meal_resilient()` thông qua kỹ thuật nới lỏng ràng buộc dần đều (Progressive Constraint Relaxation).
  - **`image_service.py`**: Tương tác với HTTP API để cào (fetch) và cache URL hình ảnh món ăn.

---

## 5. Thiết kế Cơ sở Dữ liệu (Database Design)
Hệ thống sử dụng hệ quản trị **PostgreSQL** kết hợp với ORM mạnh mẽ của Django.

**Các thực thể (Entities) cốt lõi:**
- **`UserProfile`**: Liên kết One-to-One với tài khoản User hệ thống, lưu trữ thông số sinh lý chi tiết.
- **`Recipe`**: Thư viện món ăn đã được gán nhãn (Cluster) và phân tích trung bình phân bổ Macro (Protein, Fat, Carbs, Calories).
- **`PlanGenerationEvent` & `GeneratedPlan`**: Hệ thống theo dõi lịch sử và trạng thái các truy vấn sinh thực đơn. Dữ liệu này hình thành vòng lặp phản hồi (Data Flywheel) giúp đánh giá độ hiệu quả của thuật toán tối ưu trên diện rộng.

---

## 6. Công nghệ Sử dụng (Technology Stack)

| Lớp (Layer) | Công nghệ / Framework | Vai trò trong dự án |
| :--- | :--- | :--- |
| **Backend Framework** | Django (Python) | Quản lý logic nghiệp vụ, API và Web Server. |
| **Cơ sở dữ liệu** | PostgreSQL & Django ORM | Hệ quản trị CSDL quan hệ lưu trữ dữ liệu người dùng và món ăn. |
| **AI & Machine Learning** | TensorFlow (Keras), Scikit-Learn | Chuẩn hóa dữ liệu và huấn luyện mô hình dự đoán cụm dinh dưỡng. |
| **Tối ưu hóa (Optimization)** | PuLP | Giải quyết bài toán quy hoạch tuyến tính (Linear Programming). |
| **Data Science Pipeline**| Pandas, Numpy, Jupyter | Xử lý, phân tích dữ liệu thô phục vụ nghiên cứu EDA. |
| **Giao diện (Frontend)** | HTML/CSS, Django Templates | Hiển thị giao diện tương tác và biểu đồ thống kê. |

---

## 7. Hướng dẫn Cài đặt & Triển khai (Deployment Guide)

### 7.1. Yêu cầu Hệ thống
- Python 3.10+
- PostgreSQL
- Nền tảng hỗ trợ các thư viện Data Science cơ bản.

### 7.2. Các bước triển khai cục bộ
1. **Thiết lập Môi trường Ảo (Virtual Environment):**
   ```bash
   python -m venv env
   source env/bin/activate  # Trên Windows: env\Scripts\activate
   ```
2. **Cài đặt Thư viện Phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Cấu hình Cơ sở Dữ liệu:**
   - Cập nhật thông tin kết nối PostgreSQL (User, Password, Database Name) trong file `core/settings.py`.
4. **Thực thi Migrations & Tạo Superuser:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
5. **Khởi động Server:**
   ```bash
   python manage.py runserver
   ```
   *Hệ thống quản trị và Client UI sẽ khởi chạy tại `http://127.0.0.1:8000/`*

---

## 8. Kết luận và Hướng phát triển (Conclusion & Future Work)
Dự án **DietPlanning** đã chứng minh tính khả thi của việc ứng dụng kết hợp giữa Phân loại AI (Machine Learning Classification) và Nghiên cứu Tác nghiệp (Quy hoạch tuyến tính) vào bài toán chăm sóc sức khỏe dinh dưỡng. Thuật toán tối ưu linh hoạt giúp vượt qua hạn chế của các ứng dụng gợi ý bữa ăn truyền thống vốn chỉ dựa trên nguyên tắc tìm kiếm ngẫu nhiên hoặc đếm calo thuần túy.

**Hướng phát triển trong tương lai:**
- **Recommendation Systems:** Tích hợp Collaborative Filtering để gợi ý món ăn dựa trên lịch sử đánh giá (Rating) của những người dùng có chung khẩu vị.
- **Computer Vision:** Tích hợp nhận diện hình ảnh thức ăn để ước tính lượng calo trực tiếp từ camera.
- **Theo dõi thời gian thực (Real-time tracking):** Kết nối hệ thống với API của các thiết bị đeo tay thông minh (Smartwatches) để tự động điều chỉnh năng lượng tiêu hao hàng ngày.
