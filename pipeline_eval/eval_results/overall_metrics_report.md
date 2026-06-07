# Báo cáo Tổng hợp Chỉ số Đánh giá (Evaluation Metrics)

## 1. Kết quả Trung bình Toàn cục (Global Averages)

- **Tổng số Samples (Conversations)**: 10
- **Tổng số câu QA (Total QA)**: 1986
- **Tổng số câu đúng (LLM Judge Passes)**: 1217

| Metric | Macro-Average (Trung bình các Sample) | Micro-Average (Tổng thể) |
|---|---|---|
| **BM25 Hit Rate @1** | 65.79% | 65.81% |
| **BM25 Hit Rate @3** | 81.29% | 81.40% |
| **BM25 Hit Rate @5** | 87.41% | 87.38% |
| **LLM Judge Accuracy** | 62.19% | 61.28% |
| **Cat1: Single-hop Accuracy** | 64.52% | 63.83% |
| **Cat2: Temporal Accuracy** | 70.24% | 68.54% |
| **Cat3: Multi-hop Accuracy** | 47.82% | 53.12% |
| **Cat4: Open-domain Accuracy** | 69.58% | 68.49% |
| **Cat5: Adversarial Accuracy** | 43.79% | 42.60% |

*Ghi chú:*

*- **Macro-Average**: Tính tỷ lệ cho từng Conversation, sau đó cộng lại chia đều.*
*- **Micro-Average**: Tính tổng số câu đúng trên tổng số câu hỏi của toàn bộ tập dữ liệu.*

## 2. Chi tiết từng Sample (Conversation)

| File | Conv Index | Total QA | Hits@1 | Hits@3 | Hits@5 | LLM Passes | Hit Rate@1 | Hit Rate@3 | Hit Rate@5 | LLM Accuracy | Cat1 Acc | Cat2 Acc | Cat3 Acc | Cat4 Acc | Cat5 Acc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| eval_conv_0.xlsx | 0 | 199 | 131.8 | 163.5 | 173.5 | 107 | 66.25% | 82.16% | 87.20% | 53.77% | 59.38% | 81.08% | 38.46% | 68.57% | 10.64% |
| eval_conv_1.xlsx | 1 | 105 | 74.3 | 87.7 | 95.2 | 81 | 70.79% | 83.49% | 90.71% | 77.14% | 81.82% | 92.31% | 0.00% | 81.82% | 50.00% |
| eval_conv_2.xlsx | 2 | 193 | 126.6 | 155.8 | 169.4 | 131 | 65.59% | 80.74% | 87.78% | 67.88% | 61.29% | 74.07% | 75.00% | 77.91% | 46.34% |
| eval_conv_3.xlsx | 3 | 260 | 168.8 | 205.5 | 221.9 | 173 | 64.94% | 79.04% | 85.33% | 66.54% | 72.97% | 82.50% | 54.55% | 71.17% | 45.90% |
| eval_conv_4.xlsx | 4 | 242 | 179.4 | 212.7 | 222.3 | 147 | 74.14% | 87.91% | 91.86% | 60.74% | 67.74% | 84.62% | 57.14% | 73.83% | 26.56% |
| eval_conv_5.xlsx | 5 | 158 | 87.8 | 117.5 | 130.6 | 106 | 55.57% | 74.35% | 82.68% | 67.09% | 63.33% | 75.00% | 57.14% | 79.03% | 45.71% |
| eval_conv_6.xlsx | 6 | 190 | 144.7 | 172.4 | 181.0 | 105 | 76.14% | 90.72% | 95.28% | 55.26% | 50.00% | 41.18% | 76.92% | 57.83% | 57.50% |
| eval_conv_7.xlsx | 7 | 239 | 150.1 | 198.0 | 213.8 | 121 | 62.82% | 82.84% | 89.46% | 50.63% | 66.67% | 33.33% | 30.00% | 55.93% | 50.00% |
| eval_conv_8.xlsx | 8 | 196 | 117.3 | 144.7 | 158.7 | 114 | 59.86% | 73.81% | 80.99% | 58.16% | 59.46% | 72.73% | 46.15% | 63.01% | 40.00% |
| eval_conv_9.xlsx | 9 | 204 | 126.1 | 158.8 | 168.9 | 132 | 61.81% | 77.82% | 82.80% | 64.71% | 62.50% | 65.62% | 42.86% | 66.67% | 65.22% |