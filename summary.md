Đã làm xong các phần chính sau:

- Hoàn thiện đầy đủ flow `ReAct` và `Reflexion`:
  - Actor -> Evaluator -> Reflector (khi sai) -> cập nhật `reflection_memory` -> thử lại.
- Thay mock cứng bằng runtime thật OpenAI-compatible:
  - Đọc `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` từ `.env`.
  - Bắt buộc lấy token thực tế từ `usage.total_tokens`, thiếu thì fail cứng.
- Bổ sung `adaptive_max_attempts` theo độ khó (`easy/medium/hard`) và chặn loop lặp đáp án sai.
- Hoàn thiện schema còn thiếu:
  - `JudgeResult`, `ReflectionEntry`.
- Viết lại system prompts cho Actor/Evaluator/Reflector (Evaluator/Reflector trả JSON cấu trúc).
- Mở rộng benchmark CLI:
  - `--mode real|mock`, `--sample-size`, `--seed`, `--model`.
- Nâng cấp report:
  - Giữ đúng format `report.json`/`report.md`.
  - Sinh `discussion` động từ kết quả chạy.
  - Thêm breakdown failure mode tổng hợp để tăng chiều sâu phân tích.
- Thêm script tạo dataset 100 mẫu HotpotQA deterministic.
- Cập nhật README, `.env.example`, dependencies, và test mới.
- Verify:
  - `pytest` pass toàn bộ.
  - Benchmark mock chạy ổn và sinh report hợp lệ.

Kiến thức rút ra sau bài:

- Cách xây một vòng lặp Reflexion thực tế:
  - Reflection chỉ hữu ích khi chuyển thành “memory hành động được” cho lần thử sau.
- So sánh ReAct vs Reflexion:
  - Reflexion thường tăng EM nhưng đánh đổi token/latency/attempts.
- Thiết kế evaluator “structured output” là then chốt:
  - JSON schema rõ ràng giúp pipeline ổn định và dễ debug.
- Đo token “thật” đúng cách:
  - Dựa vào `usage` từ API, không dùng estimate nếu mục tiêu là benchmark nghiêm túc.
- Adaptive attempts giúp cân bằng chi phí/chất lượng:
  - Bài dễ không cần nhiều vòng, bài khó cần thêm budget.
- Benchmark reproducible:
  - Sampling deterministic bằng seed giúp tái lập và so sánh công bằng giữa các lần chạy.
