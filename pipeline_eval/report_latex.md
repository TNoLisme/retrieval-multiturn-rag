\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts
% The preceding line is only needed to identify funding in the first footnote. If that is unneeded, please comment it out.

% Cấu hình Tiếng Việt
\usepackage[utf8]{inputenc}
\usepackage[T5]{fontenc}
\usepackage[vietnamese]{babel}

% Các gói cơ bản của IEEE
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{float}
\usepackage{tabularx}
\usepackage{booktabs}   
\usepackage{tabularx}   
\usepackage{caption}  
\usepackage{array}

\begin{document}

\title{RAG for Multi-turn Conversational AI Systems\\
}

\author{
    \IEEEauthorblockN{1\textsuperscript{st} Nguyễn Văn Thịnh}
    \IEEEauthorblockA{\textit{MSV: 23021726} \\
    % Trường Đại học Công Nghệ (UET) \\
    % Đại học Quốc Gia Hà Nội (VNU)
    }

    \\[1ex]

    \IEEEauthorblockN{2\textsuperscript{nd} Mai Đức Văn}
    \IEEEauthorblockA{\textit{MSV: 23021746} \\
    }

    \and

    \IEEEauthorblockN{3\textsuperscript{rd} Ngọ Viết Thuyết}
    \IEEEauthorblockA{\textit{MSV: 23021730} \\
    }

    \and

    \IEEEauthorblockN{4\textsuperscript{th} Nguyễn Trường Sơn}
    \IEEEauthorblockA{\textit{MSV: 23021686} \\
    }

    \\[1ex]

    \IEEEauthorblockN{5\textsuperscript{th} Nguyễn Minh Phúc}
    \IEEEauthorblockA{\textit{MSV: 23021662} \\
    }
}

\maketitle

% \begin{abstract}
% [PLACEHOLDER] Bài tóm tắt này trình bày tổng quan về việc ứng dụng Retrieval-Augmented Generation (RAG) trong các hệ thống đàm thoại hội thoại nhiều lượt (multi-turn). Chúng tôi phân tích các giới hạn của hệ thống hiện tại trong việc duy trì ngữ cảnh, đánh giá các phương pháp giải quyết và đề xuất một đường ống (pipeline) lai ghép (hybrid) để tối ưu hóa khả năng truy xuất và sinh văn bản tự nhiên.
% \end{abstract}

\begin{IEEEkeywords}
RAG, Conversational AI, Multi-turn context, LLM, Information Retrieval
\end{IEEEkeywords}

\section{GIỚI THIỆU}

Sự phát triển nhanh chóng của các mô hình ngôn ngữ lớn (LLMs) đã tạo ra những bước tiến đáng kể trong lĩnh vực trí tuệ nhân tạo. Tuy nhiên, đi cùng với những thành tựu đó là các hạn chế mang tính bản chất, tiêu biểu như việc kiến thức của mô hình bị giới hạn tại thời điểm huấn luyện và hiện tượng sinh thông tin không chính xác (hallucination). Nhằm khắc phục những vấn đề này, kiến trúc Retrieval-Augmented Generation (RAG) được đề xuất với ý tưởng kết hợp khả năng sinh của mô hình với nguồn tri thức bên ngoài. Thay vì chỉ dựa vào tham số đã học, mô hình được cung cấp thêm thông tin truy xuất từ cơ sở dữ liệu, từ đó cải thiện độ tin cậy của câu trả lời.

Dù cho thấy hiệu quả rõ rệt trong các bài toán truy vấn đơn lượt, RAG truyền thống (Naive RAG) vẫn còn nhiều hạn chế khi áp dụng vào bối cảnh hội thoại đa lượt. Khác với truy vấn đơn, nơi mỗi câu hỏi thường mang đầy đủ ngữ cảnh, hội thoại đa lượt hình thành từ chuỗi tương tác liên tục, trong đó thông tin được kế thừa và biến đổi qua từng lượt. Với đặc tính xử lý truy vấn một cách độc lập, RAG bộc lộ sự thiếu hụt trong việc nắm bắt mạch ngữ cảnh xuyên suốt, dẫn đến suy giảm hiệu quả truy xuất.

Một trong những thách thức đáng chú ý là hiện tượng mơ hồ ngữ nghĩa do đồng tham chiếu và lược bỏ thành phần câu. Trong giao tiếp tự nhiên, người dùng thường sử dụng đại từ hoặc giản lược chủ ngữ với giả định rằng ngữ cảnh đã được hiểu ngầm. Điều này khiến truy vấn hiện tại trở nên không đầy đủ về mặt thông tin khi bị tách khỏi lịch sử hội thoại, từ đó gây khó khăn cho quá trình truy xuất.

Bên cạnh đó, hội thoại thực tế thường không tuân theo một luồng chủ đề tuyến tính. Người dùng có thể chuyển sang một chủ đề mới hoặc quay lại vấn đề đã đề cập trước đó mà không có tín hiệu rõ ràng. Sự chuyển đổi chủ đề ngầm này làm cho hệ thống khó xác định phạm vi ngữ cảnh phù hợp, dễ dẫn đến việc truy xuất sai lệch hoặc thiếu liên quan.

Ngoài ra, việc duy trì toàn bộ lịch sử hội thoại bằng cách ghép nối trực tiếp vào truy vấn hiện tại tuy đơn giản nhưng không hiệu quả. Cách tiếp cận này nhanh chóng làm vượt quá giới hạn cửa sổ ngữ cảnh của mô hình, đồng thời đưa vào nhiều thông tin không cần thiết, làm giảm khả năng tập trung vào nội dung quan trọng.

Từ những hạn chế trên, có thể thấy rằng việc cải thiện hiệu quả của hệ thống hội thoại không chỉ phụ thuộc vào năng lực sinh của mô hình ngôn ngữ, mà còn nằm ở cách tổ chức và tối ưu hóa quá trình truy xuất. Báo cáo này tập trung phân tích các nguyên nhân dẫn đến suy giảm hiệu năng của Retriever trong bối cảnh đa lượt, đồng thời đề xuất các hướng tiếp cận nhằm xử lý ngữ cảnh trước truy xuất. Trọng tâm của nghiên cứu là xây dựng cơ chế tái diễn đạt truy vấn theo hướng biến mỗi câu hỏi phụ thuộc ngữ cảnh thành một câu hỏi độc lập, từ đó nâng cao độ chính xác của quá trình truy xuất và đảm bảo tính nhất quán trong toàn bộ hội thoại.


% Nhận thức rõ khoảng trống này, nhóm nghiên cứu nhận định rằng cốt lõi để nâng cấp hệ thống Conversational AI không nằm ở việc sử dụng một LLM sinh văn bản mạnh hơn, mà phải nằm ở việc tối ưu hóa module Retrieval. Báo cáo này tập trung vào các mục tiêu then chốt: (1) Phân tích cơ chế gây lỗi của bộ Retriever trong môi trường hội thoại đa lượt; (2) Đề xuất và cài đặt các giải pháp tối ưu xử lý ngữ cảnh tiền truy xuất (Pre-retrieval optimization); và (3) Đánh giá hiệu năng của các phương pháp nhằm hoàn thiện một pipeline Conversational RAG có khả năng duy trì độ chính xác cao và trải nghiệm liền mạch cho người dùng cuối.


\section{MÔ TẢ BÀI TOÁN}

Để phân tích bản chất của các giới hạn hiện tại và làm tiền đề xây dựng các phương pháp tối ưu, bài toán RAG trong hội thoại đa lượt được đặc tả hình thức hóa với các thành phần cốt lõi như sau:

\begin{table}[htbp]
\caption{Định nghĩa các yếu tố đầu vào}
\label{tab:input_resources}
\centering
\small
\begin{tabularx}{\linewidth}{
    | p{0.15\linewidth} 
    | >{\centering\arraybackslash}m{0.4\linewidth} 
    | X |
}
    \hline
    \textbf{Thành phần} & \textbf{Ký hiệu \& Định dạng} & \textbf{Mô tả} \\
    \hline
    
    Kho tri thức & 
    $\mathcal{D} = \{d_1, \dots, d_N\}$ & 
    Tập hợp các tài liệu tri thức đầu vào. \\
    \hline
    
    Lịch sử hội thoại & 
    $H_t = \{(u_1, r_1), \dots, (u_{t-1}, r_{t-1})\}$ & 
    Chuỗi các lượt tương tác tính đến thời điểm $t$. Trong đó, $u_i$ là truy vấn và $r_i$ là phản hồi tương ứng. \\
    \hline
    
    Truy vấn hiện tại & 
    $u_t$ & 
    Câu hỏi của người dùng ở lượt thứ $t$. \\
    \hline
\end{tabularx}

\end{table}


\subsection{Mô hình hóa quá trình xử lý}
Kiến trúc RAG đa lượt hoạt động dựa trên ba giai đoạn toán học tuần tự. Đầu tiên, hệ thống thực hiện hàm biến đổi ngữ cảnh $f_\theta$ để tổng hợp thông tin từ câu hỏi hiện tại $u_t$ và lịch sử hội thoại $H_t$, nhằm tạo ra một biểu diễn truy vấn tối ưu $q_t^*$:
\begin{equation}
\label{eq:q_star}
    q_t^* = f_\theta(u_t, H_t)
\end{equation}

Tiếp theo, hàm truy xuất $g_\phi$ sử dụng biểu diễn $q_t^*$ vừa được tạo để trích xuất một tập con gồm $K$ tài liệu phù hợp nhất, ký hiệu là $D_t^*$, từ kho tri thức $\mathcal{D}$:
\begin{equation} 
\label{eq:D_star}
    D_t^* = g_\phi(q_t^*, \mathcal{D})
\end{equation}

Cuối cùng, dựa trên các thông tin đã được tổng hợp và truy xuất, mô hình sinh văn bản $p_\psi$ sẽ tiến hành tính toán xác suất để đưa ra phản hồi mục tiêu $r_t$ chính xác nhất:
\begin{equation}
\label{eq:r_t}
    r_t = \arg\max_{r} p_\psi(r | q_t^*, H_t, D_t^*)
\end{equation}

\subsection{Mục tiêu tối ưu} 
Nhằm đạt được mục tiêu cuối cùng là tối ưu hóa chất lượng của phản hồi đầu ra $r_t$, các kiến trúc RAG cần giải quyết đồng thời ba nhiệm vụ trọng tâm. Cụ thể, hệ thống phải nâng cao độ chính xác của biểu diễn truy vấn $q_t^*$, đồng thời lưu trữ và khai thác một cách hiệu quả lịch sử hội thoại $H_t$ trong các phiên làm việc kéo dài. Bên cạnh đó, việc đảm bảo truy xuất tập tài liệu $D_t^*$ một cách nhanh chóng, chuẩn xác và đầy đủ cũng là yếu tố tiên quyết để nâng cao chất lượng câu trả lời cuối cùng.

\section{KHẢO SÁT CÁC PHƯƠNG PHÁP HIỆN CÓ}

Kiến trúc RAG có thể được nhìn nhận thông qua hai khía cạnh chính: \textbf{(1) Tối ưu hóa kho tri thức và cơ chế truy xuất} và \textbf{(2) Quản lý ngữ cảnh và bộ nhớ hội thoại}. Trong các hệ thống hỏi đáp đơn lượt (single-turn), khía cạnh thứ nhất đã được nghiên cứu tương đối toàn diện thông qua các phương pháp tìm kiếm và tái xếp hạng. Ngược lại, trong bối cảnh đa lượt, thách thức nổi bật hơn nằm ở khả năng duy trì và khai thác ngữ cảnh hội thoại một cách nhất quán.

Dựa trên đặc tả hình thức ở chương trước, các nghiên cứu hiện nay chủ yếu tập trung vào ba hướng tối ưu: làm rõ biểu diễn truy vấn $q_t^*$, cải thiện chất lượng tập tài liệu truy xuất $D_t^*$, và kiểm soát hiệu quả lịch sử hội thoại $H_t$. Trong đó, việc tối ưu biểu diễn truy vấn thường được triển khai thông qua một khung kiến trúc phổ biến là \textbf{RRR} (Rewrite–Retrieve–Read). Khung này bổ sung một bước tiền xử lý nhằm tái diễn đạt truy vấn, sử dụng mô hình ngôn ngữ để khôi phục các thành phần bị lược bỏ và đưa câu hỏi về dạng đầy đủ dựa trên ngữ cảnh trước đó.

Mặc dù chia sẻ cùng một khung tổng quát, các phương pháp RAG đa lượt lại khác biệt đáng kể ở cách biểu diễn và khai thác ngữ cảnh $H_t$. Xét theo tiêu chí này, có thể phân các hướng tiếp cận hiện nay thành hai nhóm chính.

Hướng thứ nhất tập trung vào \textbf{quản lý và tinh lọc bộ nhớ} (Memory Management \& Filtering). Các phương pháp thuộc nhóm này vẫn duy trì biểu diễn ngữ cảnh theo dạng tuyến tính, nhưng áp dụng các cơ chế chọn lọc để giảm nhiễu. Thay vì đưa toàn bộ lịch sử hội thoại vào mô hình, hệ thống chỉ giữ lại những thông tin được xem là quan trọng, chẳng hạn các mốc sự kiện chính hoặc các lượt tương tác có liên quan trực tiếp đến truy vấn hiện tại. Nhờ đó, mô hình có thể duy trì hiệu quả bộ nhớ dài hạn mà không vượt quá giới hạn tài nguyên. Một số đại diện tiêu biểu cho hướng tiếp cận này bao gồm \textbf{MemoChat}, \textbf{HingeMem} và \textbf{EMem}.

Hướng thứ hai tiếp cận vấn đề từ góc độ \textbf{cấu trúc hóa tri thức hội thoại} (Knowledge Structuring). Thay vì lưu trữ ngữ cảnh dưới dạng chuỗi, các phương pháp này chuyển đổi lịch sử hội thoại thành các cấu trúc có tổ chức hơn, điển hình là đồ thị tri thức. Cách biểu diễn này cho phép thiết lập các liên kết rõ ràng giữa các thực thể và sự kiện, từ đó hỗ trợ các dạng suy luận đa bước (multi-hop reasoning). Đồng thời, nó tạo ra sự kết hợp tự nhiên giữa bộ nhớ hội thoại và các thuật toán trên đồ thị. Các công trình như \textbf{StructMem}, \textbf{HippoRAG} và \textbf{EMem-G} là những ví dụ tiêu biểu cho hướng tiếp cận này.

Các tiểu mục tiếp theo sẽ phân tích chi tiết từng phương pháp theo ba khía cạnh: cơ chế kỹ thuật, ưu điểm và các hạn chế còn tồn tại. Từ đó, phần sau của báo cáo hướng tới việc xây dựng một kiến trúc kết hợp nhằm tận dụng ưu điểm của cả hai hướng tiếp cận.

% Include từng phương pháp lẻ từ thư mục methods/
\subsection{\textbf{RRR}}
\label{sec:RRR}

Theo quy trình thông thường, các hệ thống RAG vận hành dựa trên cơ chế "Truy xuất rồi Đọc" (Retrieve-then-Read). Trong cơ chế này, hệ thống đi theo một pipeline tuyến tính: tiếp nhận trực tiếp truy vấn thô của người dùng, chuyển đổi thành vector nhúng để tìm kiếm các tài liệu tương đồng trong kho tri thức, sau đó kết hợp các tài liệu thu được vào prompt nhằm phục vụ cho bước sinh câu trả lời của mô hình ngôn ngữ lớn. Cách tiếp cận này cho thấy hiệu quả trong các tác vụ đơn lượt, nhưng bộc lộ hạn chế khi phải xử lý tính liên tục và sự phụ thuộc ngữ cảnh trong hội thoại đa lượt. Nhằm khắc phục điểm yếu này, Ma và cộng sự \cite{rrr2023} đã đề xuất khung kiến trúc Rewrite–Retrieve–Read (RRR).

\subsubsection{\textbf{Ý tưởng cốt lõi}}
Phương pháp này xuất phát từ việc xử lý nguyên nhân gốc rễ gây nhiễu, đó là chất lượng của truy vấn đầu vào. Thay vì thực hiện truy xuất trực tiếp trên một câu hỏi có thể mơ hồ hoặc chứa nhiều thành phần bị lược bỏ, hệ thống tiến hành khôi phục ngữ cảnh từ lịch sử hội thoại để tái diễn đạt truy vấn thành một dạng đầy đủ và độc lập. Việc chuẩn hóa đầu vào theo cách này mang lại hai lợi ích rõ rệt: thứ nhất, giúp quá trình tìm kiếm trong kho tri thức trở nên chính xác hơn; thứ hai, cung cấp một bối cảnh rõ ràng để mô hình ngôn ngữ sinh ra phản hồi có chất lượng cao hơn ở bước cuối.

\subsubsection{\textbf{Phương pháp triển khai}}
Kiến trúc RRR được triển khai thông qua ba thành phần nối tiếp, tương ứng với các giai đoạn trong quy trình xử lý tổng quát. Trước hết, bộ viết lại (Query Rewriter) đảm nhận vai trò thực thi hàm tiền xử lý $f_\theta$ như trong công thức \eqref{eq:q_star}. Thành phần này nhận truy vấn thô $u_t$ cùng lịch sử hội thoại $H_t$, sau đó diễn giải và chuyển đổi thành biểu diễn truy vấn đã được tái cấu trúc $q_t^*$.

Tiếp theo, bộ truy xuất (Retriever), tương ứng với hàm $g_\phi$ trong công thức \eqref{eq:D_star}, sử dụng truy vấn $q_t^*$ làm điểm neo để xác định và trích xuất tập tài liệu liên quan nhất $D_t^*$ từ kho tri thức $\mathcal{D}$.

Cuối cùng, bộ đọc (Reader) đóng vai trò là mô hình sinh văn bản $p_\psi$ như được mô tả trong công thức \eqref{eq:r_t}. Thành phần này tổng hợp thông tin từ truy vấn, lịch sử hội thoại và các tài liệu đã truy xuất để sinh ra phản hồi cuối cùng $r_t$.

Nhìn chung, khung kiến trúc RRR đóng vai trò như một nền tảng cơ sở cho các hệ thống RAG trong bối cảnh hội thoại đa lượt. Nó thiết lập cấu trúc cần thiết để tích hợp các kỹ thuật xử lý ngữ cảnh nâng cao, vốn sẽ được trình bày chi tiết hơn ở các tiểu mục tiếp theo.

\subsection{\textbf{MemoChat}}
\label{sec:MemoChat}

Khung kiến trúc RRR không cung cấp một cơ chế cụ thể để kiểm soát sự gia tăng kích thước của lịch sử hội thoại $H_t$. Nhằm giải quyết khoảng trống này, Tan và cộng sự \cite{memochat2023} đã đề xuất phương pháp MemoChat.

\subsubsection{\textbf{Ý tưởng và hướng tiếp cận}}

Thay vì duy trì toàn bộ văn bản thô như trong các hệ thống RAG cơ bản, MemoChat được xây dựng dựa trên ý tưởng mô phỏng hành vi "ghi chép" của con người. Cụ thể, phương pháp này tiến hành tinh chỉnh các mô hình ngôn ngữ để chúng có khả năng tự động chắt lọc và tóm tắt các đoạn hội thoại trước đó thành các "bản ghi chú" (memos) có cấu trúc. Các bản ghi chú này đóng vai trò như một dạng bộ nhớ dài hạn, giúp biểu diễn lịch sử $H_t$ theo cách cô đọng và có tổ chức hơn.

\subsubsection{\textbf{Phương pháp triển khai}}

Theo kiến trúc được trình bày trong \cite{memochat2023}, MemoChat duy trì mạch hội thoại thông qua một quy trình lặp gồm ba giai đoạn chính. Trước hết, ở bước ghi nhớ (Memorization), khi phần bộ nhớ ngắn hạn, bao gồm các lượt tương tác gần nhất đạt tới giới hạn token, hệ thống sẽ kích hoạt một tiến trình nền để rà soát lại đoạn hội thoại này. Từ đó, các thông tin quan trọng như chủ đề, sự kiện hay đặc điểm người dùng được trích xuất và nén thành một bản ghi chú mới để lưu trữ.

Tiếp theo là giai đoạn truy xuất, trong đó truy vấn $u_t$ (hoặc phiên bản đã được tái cấu trúc của nó) được sử dụng để tìm kiếm các bản ghi chú có liên quan trong bộ nhớ dài hạn. Cuối cùng, ở bước sinh phản hồi, mô hình ngôn ngữ nhận một prompt tổng hợp bao gồm các bản ghi chú đã truy xuất, ngữ cảnh hội thoại ngắn hạn và truy vấn hiện tại, từ đó tạo ra câu trả lời cuối cùng.

Để hỗ trợ quá trình quản lý và đối chiếu thông tin, mỗi bản ghi chú không được lưu trữ dưới dạng văn bản tự do mà tuân theo một cấu trúc dữ liệu rõ ràng. Cấu trúc này được minh họa trong Bảng \ref{tab:memo_structure}.


    \begin{table}[htbp]
        \caption{Cấu trúc dữ liệu cốt lõi của một bản ghi chú (Memo)}
        \label{tab:memo_structure}
        \centering
        \renewcommand{\arraystretch}{1.3}
        \begin{tabular}{|p{0.15\linewidth}|p{0.40\linewidth}|p{0.2\linewidth}|}
        \hline
        \textbf{Trường dữ liệu} & \textbf{Mô tả chức năng} & \textbf{Ví dụ} \\
        \hline
        \textbf{Chủ đề} & Từ khóa chính để đối chiếu vector truy xuất. & quantum physics, businesss,... \\
        \hline
        \textbf{Tóm tắt} & Lưu trữ cốt lõi thông tin dưới dạng văn bản ngắn gọn, loại bỏ ngôn ngữ giao tiếp dư thừa. & Bot explains Super-position ... \\
        \hline
        \textbf{Đoạn hội thoại} & Ghi lại nội dung từng lượt trao đổi cụ thể. & User: asked... Bot: replied... \\
        \hline
        \end{tabular}
    \end{table}

\subsubsection{\textbf{Ưu điểm và nhược điểm}}

Phương pháp này giúp giảm đáng kể áp lực lên cửa sổ ngữ cảnh và cải thiện độ trễ phản hồi nhờ cơ chế nén thông tin hiệu quả. Các bản ghi chú đóng vai trò như một lớp tri thức trung gian, hỗ trợ hệ thống duy trì tính nhất quán trong các phiên hội thoại kéo dài.

Tuy nhiên, quá trình tóm tắt tự động về bản chất là một dạng nén có tổn hao, do đó có thể làm mất đi các chi tiết nhỏ hoặc sắc thái ngôn ngữ ban đầu của người dùng. Ngoài ra, việc tạo ghi chú theo các chu kỳ cố định không chỉ tiêu tốn tài nguyên xử lý nền mà còn tiềm ẩn nguy cơ trộn lẫn các chủ đề khác nhau khi thông tin bị gom lại một cách cưỡng ép. Việc thiếu các cơ chế hợp nhất và bảo trì bộ nhớ động cũng khiến hệ thống gặp khó khăn khi mở rộng, đặc biệt trong các kịch bản hội thoại rất dài, nơi nguy cơ phân mảnh thông tin và suy giảm độ chính xác truy xuất trở nên rõ rệt.
 
\subsection{\textbf{HingeMem}}
\label{sec:HingeMem}

Mặc dù MemoChat đã xây dựng được một cơ chế bộ nhớ dài hạn thông qua các bản ghi chú, cách tóm tắt theo chu kỳ tĩnh vẫn dẫn đến sự dư thừa trong tính toán và tiềm ẩn nguy cơ nhiễu chủ đề cục bộ. Nhằm khắc phục hạn chế này, Zhong và Gao \cite{hingemem2026} đề xuất kiến trúc HingeMem với mục tiêu điều chỉnh quá trình ghi nhớ và truy xuất theo sự biến động thực tế của hội thoại.

\subsubsection{\textbf{Ý tưởng và hướng tiếp cận}}

HingeMem thay đổi cách tiếp cận từ định lượng sang định tính trong việc quản lý bộ nhớ. Thay vì dựa vào số lượng token để quyết định thời điểm cập nhật, phương pháp này kế thừa \textit{Lý thuyết phân đoạn sự kiện} (Event Segmentation Theory) trong khoa học nhận thức. Theo đó, hệ thống không ghi nhận thông tin một cách liên tục mà chỉ tạo ra các \textit{"điểm neo"} (hinges) khi phát hiện sự thay đổi đáng kể trong bối cảnh hội thoại. Cách tiếp cận này giúp giảm thiểu các lần cập nhật không cần thiết, đồng thời cho phép chuyển từ cơ chế truy xuất Top-$K$ cố định sang một quy trình thích ứng theo từng truy vấn cụ thể.

\subsubsection{\textbf{Phương pháp triển khai}}

HingeMem vận hành dựa trên hai cơ chế bổ trợ nhằm tối ưu đồng thời quá trình ghi và truy xuất bộ nhớ. Trước hết, ở giai đoạn ghi nhớ kích hoạt theo biên (Boundary-triggered Writing), hệ thống liên tục theo dõi trạng thái ngữ cảnh thông qua một không gian sự kiện ký hiệu là $\mathcal{E}_t$, được định nghĩa như sau:
\[
\mathcal{E}_t = \{e_{person}, e_{time}, e_{location}, e_{topic}\}
\]

Trong đó:
\vspace{0.1cm}
\begin{center}
    \begin{tabular}{r l}
        $e_{person}$ : & đại diện cho các thực thể liên quan \\
        $e_{time}$ : & là mốc thời gian \\
        $e_{location}$ : & là không gian sự kiện \\
        $e_{topic}$ : & là chủ đề thảo luận.
    \end{tabular}
\end{center}
\vspace{0.1cm}

Việc đóng gói chuỗi hội thoại thành một phân đoạn chỉ được kích hoạt khi hệ thống phát hiện sự thay đổi trạng thái, tức là khi $\Delta \mathcal{E} \neq 0$ giữa các lượt tương tác.

Ở chiều ngược lại, quá trình truy xuất được thực hiện theo cơ chế thích ứng truy vấn (Query-Adaptive Retrieval). Thay vì áp dụng một ngưỡng Top-$K$ cố định, hệ thống tiến hành phân tích truy vấn hiện tại $u_t$ để điều hướng trực tiếp đến các thành phần liên quan trong không gian sự kiện $\mathcal{E}$. Nhờ đó, phạm vi tìm kiếm được thu hẹp đáng kể ngay từ đầu. Đồng thời, hệ thống đánh giá mức độ phức tạp của truy vấn để xác định độ sâu truy xuất phù hợp và chủ động dừng khi tập tài liệu $D_t^*$ đã đủ thông tin, qua đó hạn chế nhiễu và giảm chi phí tính toán.

\subsubsection{\textbf{Ưu nhược điểm}}

Cách tiếp cận này giúp tối ưu chi phí vận hành nhờ cơ chế kích hoạt theo biên sự kiện, loại bỏ các thao tác tóm tắt lặp lại không cần thiết. Việc tổ chức bộ nhớ theo các phân đoạn sự kiện cũng góp phần duy trì tính toàn vẹn của ngữ cảnh, đồng thời hỗ trợ cơ chế truy xuất thích ứng giữ cho tập tài liệu $D_t^*$ luôn gọn và phù hợp với truy vấn.

Tuy nhiên, hiệu quả của HingeMem phụ thuộc đáng kể vào khả năng nhận diện và suy luận của mô hình nền tảng. Nếu việc phát hiện sự thay đổi trong tập thực thể $\mathcal{E}$ không chính xác, cấu trúc bộ nhớ có thể bị phân mảnh hoặc lệch ngữ cảnh, gây khó khăn cho quá trình truy xuất. Bên cạnh đó, các cơ chế định tuyến và dừng truy xuất thích ứng đòi hỏi năng lực suy luận tương đối cao, khiến phương pháp này khó đạt hiệu quả khi triển khai với các mô hình ngôn ngữ nhỏ hoặc hạn chế về năng lực.

\subsection{\textbf{StructMem}}
\label{sec:StructMem}

Như đã phân tích, các hệ thống RAG hội thoại hiện tại thường bộc lộ nhiều hạn chế: MemoChat dễ gây "nhiễu chủ đề" và mất thông tin do tóm tắt tĩnh, trong khi HingeMem đối mặt với rủi ro phân mảnh logic và phụ thuộc quá lớn vào năng lực LLM do phải liên tục bám sát biên sự kiện. Ở mức tổng quát hơn, các kiến trúc này thường rơi vào hai cực đoan: Flat Memory có xu hướng làm đứt gãy ngữ cảnh, trong khi Graph Memory lại kéo theo chi phí tính toán rất lớn. Để khắc phục vấn đề này, StructMem đề xuất cơ chế Liên kết cấp độ sự kiện (Event-Level Binding), trong đó lịch sử hội thoại được cấu trúc hóa thành các sự kiện có gắn neo thời gian, giúp mô hình hiểu rõ tại sao và khi nào một thông tin xuất hiện.

\subsubsection{\textbf{Ý tưởng và hướng tiếp cận}}

StructMem không cập nhật cấu trúc bộ nhớ sau mỗi lượt hội thoại. Thay vào đó, hệ thống sử dụng cơ chế lưu đệm để tích lũy thông tin và thực hiện xử lý theo lô định kỳ nhằm tạo ra các khối kiến thức. Cách tiếp cận này giúp loại bỏ gánh nặng xử lý nền liên tục, đồng thời chuyển cơ chế truy xuất sang dạng hợp nhất xuyên sự kiện, nơi tri thức đã được tổng hợp sẵn ở mức trừu tượng cao hơn. Nhờ vậy, hệ thống có thể đáp ứng hiệu quả hơn đối với các truy vấn đa lượt phức tạp.

\subsubsection{\textbf{Phương pháp triển khai}}

StructMem vận hành thông qua một số cơ chế cốt lõi nhằm tối ưu đồng thời quá trình ghi và truy xuất bộ nhớ. Trước hết, hệ thống thực hiện trích xuất góc nhìn kép (Dual-Perspective Extraction), trong đó ngữ cảnh được biểu diễn dưới dạng các neo thời gian (Temporal Anchoring). Mỗi neo thời gian bao gồm hai thành phần: mục thông tin thực tế, chứa các dữ kiện khách quan mô tả nội dung sự kiện, và mục thông tin quan hệ (Relational Entries), phản ánh các yếu tố ngữ dụng như ý định người dùng, quan hệ nhân quả và phụ thuộc thời gian giữa các sự kiện.

Song song với đó, cơ chế hợp nhất xuyên sự kiện được áp dụng để tổ chức lại bộ nhớ. Thay vì cập nhật liên tục, hệ thống lưu các sự kiện vào một vùng đệm. Khi lượng dữ liệu đạt đến ngưỡng nhất định, một tiến trình tổng hợp sẽ được kích hoạt để xây dựng lớp tri thức trừu tượng, hỗ trợ các dạng suy luận đa bước.

Trong giai đoạn truy xuất, hệ thống ưu tiên khai thác các thông tin đã được tổng hợp hoặc nằm trong bộ đệm. Nếu truy vấn có thể được giải quyết ở mức này, quá trình truy xuất từ cơ sở dữ liệu thô sẽ được bỏ qua, qua đó giảm đáng kể nhiễu và chi phí xử lý.

\subsubsection{\textbf{Ưu nhược điểm}}

Về mặt ưu điểm, StructMem cho thấy hiệu quả sử dụng tài nguyên cao nhờ giảm số lượng token tiêu thụ, số lần gọi mô hình và thời gian xử lý so với các phương pháp bộ nhớ đồ thị trước đây. Hệ thống đặc biệt phù hợp với các bài toán yêu cầu suy luận đa bước và xử lý thông tin theo trục thời gian, thể hiện hiệu năng vượt trội trên các bộ dữ liệu như LOCOMO. Ngoài ra, cấu trúc phân cấp giúp tăng độ bền của hệ thống, giảm mức độ ảnh hưởng của các lỗi trích xuất thực thể so với các kiến trúc đồ thị truyền thống.

Tuy nhiên, phương pháp này vẫn tồn tại một số hạn chế. Nếu quá trình trích xuất góc nhìn kép ban đầu không chính xác, các mối quan hệ giữa sự kiện có thể bị phân tách không hợp lý, gây khó khăn cho truy xuất về sau. Bên cạnh đó, tại thời điểm kích hoạt cơ chế hợp nhất, hệ thống cần xử lý một lượng lớn thông tin trong một lần, dẫn đến độ trễ cục bộ cao hơn so với các bước hội thoại thông thường.

\subsection{\textbf{HippoRAG}}
\label{sec:hipporag}

HippoRAG tối ưu hóa hệ thống Conversational RAG bằng cách tái cấu trúc cơ chế lưu trữ dữ liệu thông qua đồ thị tri thức, từ đó đảm bảo thông tin được bảo toàn và duy trì mạch logic xuyên suốt hội thoại.

\subsubsection{\textbf{Ý tưởng cốt lõi}}

HippoRAG được xây dựng dựa trên cảm hứng từ thuyết Bổ trợ học tập (Complementary Learning Systems) trong thần kinh học, mô phỏng chức năng của hồi hải mã (hippocampus) nhằm hình thành một dạng “trí nhớ liên tưởng” cho mô hình ngôn ngữ. Thay vì xử lý các thông tin rời rạc, hệ thống xây dựng một đồ thị tri thức (Knowledge Graph) để liên kết các thực thể và quan hệ giữa chúng. Nhờ đó, HippoRAG có thể thực hiện suy luận đa bước và duy trì tính nhất quán của thông tin trong các ngữ cảnh phức tạp.

\subsubsection{\textbf{Phương pháp triển khai}}

Quy trình vận hành của HippoRAG được tổ chức thành hai giai đoạn chính, dựa trên sự kết hợp giữa cấu trúc đồ thị tri thức và cơ chế lan truyền xác suất.

Trong giai đoạn lập chỉ mục, hệ thống chuyển đổi tri thức từ văn bản phi cấu trúc sang dạng đồ thị liên kết. Cụ thể, hệ thống sử dụng các mô hình ngôn ngữ để trích xuất các thực thể và quan hệ từ văn bản. Các thành phần này sau đó được ánh xạ thành các nút và cạnh trong đồ thị tri thức, tạo thành một không gian biểu diễn có cấu trúc cho toàn bộ dữ liệu.

Ở giai đoạn truy xuất (Retrieval), HippoRAG không dựa trên độ tương đồng vector đơn thuần mà triển khai một quy trình truy xuất liên tưởng. Với một truy vấn $q$, hệ thống trích xuất tập thực thể truy vấn $E_q \subset V$, trong đó các nút này đóng vai trò là nguồn phát tín hiệu trên đồ thị. Để xác định các nút liên quan nhất, hệ thống áp dụng thuật toán Personalized PageRank (PPR), trong đó trạng thái ổn định của phân phối xác suất $\mathbf{v}$ được xác định theo công thức lặp:
\begin{equation}
\mathbf{v}^{(t+1)} = (1 - \alpha) \mathbf{M}\mathbf{v}^{(t)} + \alpha \mathbf{p}
\end{equation}

Trong công thức trên, $\alpha \in (0, 1)$ là hệ số cản (damping factor), thường được thiết lập $\alpha = 0.15$; $\mathbf{M}$ là ma trận chuyển vị liên kết của đồ thị $G$; và $\mathbf{p}$ là vector cá nhân hóa, trong đó các giá trị khác 0 chỉ xuất hiện tại các vị trí tương ứng với các nút thuộc tập $E_q$.

Sau khi quá trình lan truyền hội tụ, các nút có giá trị cao nhất trong $\mathbf{v}$ sẽ được lựa chọn. Hệ thống sau đó truy hồi các đoạn văn bản gốc tương ứng với các nút này để xây dựng ngữ cảnh đầu vào cho mô hình sinh.

\subsubsection{textbf{Ưu nhược điểm}}

HippoRAG cho thấy nhiều ưu điểm đáng chú ý trong việc tối ưu hóa truy xuất tri thức. Trước hết, hệ thống có khả năng thực hiện suy luận đa bước trong một lần truy xuất duy nhất thông qua cơ chế lan truyền trên đồ thị, thay vì phải lặp lại nhiều vòng như các phương pháp truyền thống. Điều này giúp cải thiện đáng kể hiệu suất, với mức tăng độ chính xác lên tới 20\% trên các bộ dữ liệu hỏi đáp đa bước. Đồng thời, việc giảm số vòng truy xuất cũng giúp hệ thống tiết kiệm chi phí tính toán và thời gian xử lý, với tốc độ nhanh hơn từ 6–13 lần và chi phí thấp hơn từ 10–30 lần so với các phương pháp truy xuất lặp.

Bên cạnh đó, nhờ sử dụng thuật toán PageRank cá nhân hóa, HippoRAG có khả năng phát hiện các mối liên kết gián tiếp giữa các thực thể, ngay cả khi chúng không chia sẻ từ khóa trực tiếp với truy vấn ban đầu.

Tuy nhiên, hiệu quả của hệ thống phụ thuộc lớn vào chất lượng của bước trích xuất thực thể và quan hệ. Các sai sót trong quá trình nhận diện thực thể (NER) hoặc trích xuất tri thức (OpenIE) có thể lan truyền và gây sai lệch trong toàn bộ quá trình truy xuất. Ngoài ra, việc chuyển đổi từ ngữ cảnh văn bản sang biểu diễn thực thể có thể làm mất đi một phần thông tin ngữ cảnh quan trọng, dẫn đến sự đánh đổi giữa tính khái quát và độ chi tiết của nội dung.

\subsection{\textbf{EMem(G)} - Enhanced Memory with Graph}
\label{sec:Emem}

EMem(G) là một hệ thống bộ nhớ dành cho AI Agent, được thiết kế nhằm lưu trữ và quản lý lịch sử hội thoại một cách có tổ chức, từ đó giúp Agent duy trì khả năng ghi nhớ dài hạn và đảm bảo tính nhất quán trong tương tác với người dùng. Thay vì lưu trữ dưới dạng văn bản tuyến tính, EMem(G) biểu diễn thông tin dưới dạng đồ thị, trong đó các dữ kiện được ánh xạ thành các thực thể và các mối quan hệ liên kết. Nhờ cấu trúc này, hệ thống không chỉ ghi nhận nội dung đã trao đổi mà còn nắm bắt được bối cảnh và các liên kết logic giữa các thông tin, qua đó hỗ trợ hiệu quả cho việc xử lý các truy vấn phức tạp trong hội thoại dài.

\subsubsection{\textbf{Ý tưởng cốt lõi}}

Khác với cơ chế RAG truyền thống vốn chủ yếu dựa trên tìm kiếm theo độ tương đồng ngữ nghĩa, EMem(G) xây dựng một hệ thống bộ nhớ dựa trên đồ thị (Graph-based Memory) để lưu trữ trực tiếp các thực thể và quan hệ được trích xuất từ lịch sử hội thoại. Trọng tâm của phương pháp nằm ở việc chuyển đổi các sự kiện rời rạc thành một mạng lưới tri thức có cấu trúc, qua đó cho phép Agent duy trì và khai thác các liên kết logic phức tạp giữa các thông tin theo thời gian.

\subsubsection{\textbf{Phương pháp triển khai}}

Quy trình vận hành của EMem(G) được tổ chức thành ba giai đoạn chính, tương ứng với các bước cập nhật, truy xuất và hợp nhất ngữ cảnh.

Ở giai đoạn trích xuất và cập nhật, mỗi khi xuất hiện một lượt hội thoại mới $H_t$ tại thời điểm $t$, hệ thống kích hoạt tiến trình cập nhật bộ nhớ. Quá trình này bao gồm hai bước chính. Trước hết là trích xuất tri thức, trong đó mô hình ngôn ngữ được sử dụng để phân tích cú pháp và ngữ nghĩa nhằm xác định các thực thể $e \in V$ và các quan hệ liên quan. Tiếp theo là cập nhật đồ thị, nơi các thực thể và quan hệ này được đưa vào cấu trúc đồ thị; nếu một thực thể đã tồn tại, hệ thống sẽ cập nhật các liên kết mới thay vì tạo bản sao.

Trong giai đoạn truy xuất dựa trên đồ thị, EMem(G) không thực hiện tìm kiếm dựa trên độ tương đồng vector mà khai thác trực tiếp cấu trúc liên kết giữa các thực thể. Khi nhận truy vấn $q$, hệ thống xác định các thực thể trọng tâm trong câu hỏi và sử dụng chúng làm điểm khởi đầu để truy ngược thông tin thông qua các quan hệ tương ứng. Nhờ cơ chế này, hệ thống có khả năng kết nối các thông tin xuất hiện ở các thời điểm khác nhau trong hội thoại, cho phép duy trì mạch ngữ cảnh xuyên suốt.

Giai đoạn cuối cùng là hợp nhất ngữ cảnh, nhằm xây dựng đầu vào tối ưu cho mô hình sinh. Tại đây, thông tin truy xuất từ đồ thị (long-term memory) được kết hợp với các lượt hội thoại gần nhất trong cửa sổ ngữ cảnh (short-term memory). Một prompt hoàn chỉnh $P_{final}$ được xây dựng theo công thức:
\begin{equation}
P_{final} = \text{Prompt}(Memory_{graph} \oplus Context_{recent})
\end{equation}
Cách hợp nhất này đảm bảo rằng phản hồi được sinh ra vừa chính xác về mặt tri thức đã tích lũy, vừa phù hợp với diễn biến hiện tại của hội thoại.

\subsubsection{\textbf{Ưu, nhược điểm}}

Về mặt ưu điểm, EMem(G) cho phép duy trì ngữ cảnh dài hạn mà không bị ràng buộc bởi giới hạn cửa sổ ngữ cảnh, nhờ việc nén thông tin thành các nút và cạnh trong đồ thị. Hệ thống đặc biệt hiệu quả trong các tình huống yêu cầu liên kết thông tin xuyên suốt nhiều lượt hội thoại, đồng thời giảm đáng kể số lượng token cần thiết do chỉ lưu giữ phần cốt lõi của tri thức.

Tuy nhiên, việc biểu diễn thông tin hội thoại dưới dạng đồ thị cũng tồn tại những hạn chế nhất định. Quá trình chuyển đổi nội dung tự nhiên sang các cấu trúc như bộ ba (S, P, O) có thể làm mất đi một phần sắc thái ngữ nghĩa hoặc cảm xúc của người dùng. Bên cạnh đó, việc liên tục trích xuất thực thể và cập nhật đồ thị sau mỗi lượt hội thoại có thể làm gia tăng độ trễ nếu không được tối ưu hóa hợp lý.


\section{Đề xuất hướng tiếp cận}

Trong nghiên cứu này, chúng em đề xuất hai hướng tiếp cận nhằm tái cấu trúc truy vấn hội thoại đa lượt thành truy vấn độc lập $Q_{final}$. Hai phương pháp được thiết kế theo mối quan hệ kế thừa, trong đó \textbf{Compression-Centric Pipeline} đóng vai trò như một baseline đơn giản, và \textbf{State-Centric Adaptive Pipeline} được phát triển như một phiên bản mở rộng nhằm khắc phục các hạn chế của phương pháp không trạng thái.

Trong mỗi lượt truy vấn, quy trình xử lý sẽ bắt đầu với một nhóm đầu vào chung cơ bản bao gồm:

\vspace{0.1cm}
\begin{center}
    \begin{tabular}{r p{0.6\linewidth}}
        \textbf{$u_t$} : & Truy vấn hiện tại của người dùng \\
        \textbf{$H_t^{short}$} : & Bộ nhớ ngắn hạn (Active Chat) chứa các lượt tương tác gần nhất, chưa được nén, giới hạn trong ngưỡng token cho phép \textbf{$[0, \tau_{token}]$}. \\
        \textbf{$\mathcal{M}$} : & Kho trí nhớ Memos Database (tập con của kho tri thức $\mathcal{D}$), lưu trữ các bản ghi chú được nén dựa trên cơ chế của MemoChat \cite{memochat2023} \\
    \end{tabular}
\end{center}

Và đầu ra mong muốn:

\begin{center}
    \begin{tabular}{r p{0.6\linewidth}}
        \textbf{$q_t^*$} : & Truy vấn được viết lại, đầy đủ thông tin định danh, có tính độc lập cao, sẵn sàng cho mô hình Reader cuối cùng xử lý và đưa ra câu trả lời chính xác. \\
    \end{tabular}
\end{center}
\vspace{0.1cm}
\subsection{\textbf{Hướng tiếp cận 1: Compression-Centric Pipeline}}
\label{sec:Approach1}

\textit{Compression-Centric Pipeline} được xây dựng như một hướng tiếp cận nền tảng nhằm giải quyết bài toán hội thoại đa lượt thông qua cơ chế nén bối cảnh chủ động. Thay vì sử dụng biểu diễn trạng thái tường minh, phương pháp này tập trung vào việc tối ưu hóa cửa sổ ngữ cảnh bằng cách chuyển đổi lịch sử hội thoại thô thành các bản ghi nhớ (Memo) dựa trên kiến trúc MemoChat~\cite{memochat2023}, sau đó thực hiện truy xuất dựa trên ngữ nghĩa để tái cấu trúc truy vấn $q_t^*$. Cách tiếp cận này đóng vai trò như một baseline đơn giản nhưng hiệu quả, làm tiền đề cho các cơ chế kiểm soát ngữ cảnh nâng cao hơn ở các kiến trúc mở rộng sau này.

\begin{figure}[h]
    \centering
    \includegraphics[width=0.5\textwidth]{figures/pipeline_Hingemem_Memo_History_NoState.jpg}
    \caption{Sơ đồ luồng xử lý Compression-Centric tập trung vào nén bối cảnh.}
    \label{fig:method2}
\end{figure}

Quy trình xử lý được tổ chức thành ba giai đoạn tuần tự như sau:

\paragraph{Giai đoạn 1: Phát hiện biên chủ đề (Topic Boundary Detection).}
Tại mỗi lượt hội thoại mới $u_t$, hệ thống áp dụng thuật toán \textit{HingMem} để xác định xem lượt hội thoại hiện tại có đánh dấu sự chuyển đổi chủ đề so với lịch sử trước đó hay không. Cụ thể, mỗi lượt thoại được mã hóa thành vector biểu diễn ngữ nghĩa thông qua mô hình SentenceTransformer (\texttt{multi-qa-mpnet-base-dot-v1}). Với mỗi vị trí $i$ trong dãy hội thoại, hệ thống tính độ tương đồng cosine giữa vector trung bình của cửa sổ bên trái $\mathbf{v}_i^{(\text{left})}$ và cửa sổ bên phải $\mathbf{v}_i^{(\text{right})}$:
\begin{equation}
    \text{sim}(i) = \cos\!\left(\mathbf{v}_i^{(\text{left})},\; \mathbf{v}_i^{(\text{right})}\right), \quad
    \mathbf{v}_i^{(\text{side})} = \frac{1}{|W|}\sum_{j \in W_i^{(\text{side})}} \mathbf{e}_j
\end{equation}
trong đó $W_i^{(\text{left})}$ và $W_i^{(\text{right})}$ là tập chỉ số của cửa sổ trượt kích thước $w$ bên trái và bên phải vị trí $i$. Dãy điểm tương đồng thô được làm mượt bằng bộ lọc trung bình động:
\begin{equation}
    \tilde{s}_i = \frac{1}{k}\sum_{j=i-\lfloor k/2\rfloor}^{i+\lfloor k/2\rfloor} \text{sim}(j)
\end{equation}
Một ngưỡng động được xác định dựa trên phân phối thống kê của dãy đã làm mượt:
\begin{equation}
    \delta = \mu_{\tilde{s}} - 0.8\,\sigma_{\tilde{s}}
\end{equation}
Vị trí $i$ được xác định là biên chủ đề nếu thỏa mãn đồng thời ba điều kiện: (i) $\tilde{s}_i$ là cực tiểu cục bộ, tức $\tilde{s}_i < \tilde{s}_{i-1}$ và $\tilde{s}_i < \tilde{s}_{i+1}$; (ii) $\tilde{s}_i < \delta$; và (iii) khoảng cách từ biên trước đó tới $i$ không nhỏ hơn độ dài đoạn tối thiểu $\ell_{\min}$. Kết quả của giai đoạn này là tập hợp các đoạn hội thoại $\mathcal{S} = \{S_1, S_2, \ldots, S_m\}$, mỗi đoạn tương ứng với một chủ đề nhất quán.

\paragraph{Giai đoạn 2: Nén đoạn hội thoại thành Memo (Compression).}
Mỗi đoạn hội thoại $S_k \in \mathcal{S}$ sau khi được phân đoạn sẽ được đưa vào mô hình ngôn ngữ lớn (LLM) thông qua một prompt có cấu trúc để tạo ra một Memo ngắn gọn $M_k$. Quá trình nén được định nghĩa như sau:
\begin{equation}
    M_k = \text{LLM}\!\left(\mathcal{P}_{\text{compress}},\; S_k\right)
\end{equation}
trong đó $\mathcal{P}_{\text{compress}}$ là prompt hướng dẫn mô hình trích xuất các thực thể quan trọng, sự kiện nổi bật và thông tin ngữ cảnh cốt lõi từ đoạn $S_k$, đồng thời loại bỏ các chi tiết dư thừa. Tập hợp các Memo $\mathcal{M} = \{M_1, M_2, \ldots, M_m\}$ đóng vai trò là bộ nhớ ngoài nén của toàn bộ lịch sử hội thoại, thay thế cho việc lưu trữ toàn bộ ngữ cảnh thô trong cửa sổ ngữ cảnh.

\paragraph{Giai đoạn 3: Truy xuất Memo và viết lại truy vấn (Retrieval \& Query Rewriting).}
Khi người dùng đặt câu hỏi $q_t$ tại lượt $t$, hệ thống thực hiện truy xuất ngữ nghĩa để lấy $K$ Memo liên quan nhất từ $\mathcal{M}$:
\begin{equation}
    \mathcal{M}_{\text{top-}K} = \operatorname*{arg\,top\text{-}K}_{M_k \in \mathcal{M}}\; \cos\!\left(\mathbf{e}_{q_t},\; \mathbf{e}_{M_k}\right)
\end{equation}
trong đó $\mathbf{e}_{q_t}$ và $\mathbf{e}_{M_k}$ là các vector nhúng của câu hỏi và Memo tương ứng. Tập Memo được truy xuất $\mathcal{M}_{\text{top-}K}$ sau đó được ghép nối với câu hỏi gốc $q_t$ để tạo thành ngữ cảnh bổ sung, và LLM thực hiện tái cấu trúc truy vấn:
\begin{equation}
    q_t^* = \text{LLM}\!\left(\mathcal{P}_{\text{rewrite}},\; q_t,\; \mathcal{M}_{\text{top-}K}\right)
\end{equation}

Câu hỏi được viết lại $q_t^*$ mang đầy đủ bối cảnh lịch sử liên quan và được sử dụng như đầu vào cuối cùng cho hệ thống sinh câu trả lời. Cách tiếp cận này đảm bảo rằng thông tin cần thiết được cung cấp cho mô hình mà không cần nạp toàn bộ lịch sử hội thoại vào cửa sổ ngữ cảnh, từ đó giảm đáng kể chi phí tính toán trong khi vẫn duy trì chất lượng phản hồi. Tuy nhiên, do không có cơ chế biểu diễn trạng thái tường minh, pipeline này vẫn phụ thuộc hoàn toàn vào chất lượng của quá trình nén và truy xuất, tạo ra khoảng trống cho các phương pháp mở rộng dựa trên state nhằm kiểm soát ngữ cảnh chính xác hơn.

\subsection{Hướng tiếp cận 2: State-Centric Adaptive Pipeline}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\textwidth]{figures/pipeline_Hingemem_Memo_State.png}
    \caption{Sơ đồ luồng xử lý State-Centric với cơ chế kiểm soát trạng thái.}
    \label{fig:method1}
\end{figure}

Kế thừa trực tiếp từ \textit{Compression-Centric Pipeline} (không sử dụng trạng thái tường minh), hướng tiếp cận này được mở rộng bằng cách tích hợp thêm một cơ chế \textbf{biểu diễn trạng thái ngữ cảnh} nhằm khắc phục hạn chế cốt lõi của phương pháp trước đó: sự phụ thuộc hoàn toàn vào truy xuất Memo và thiếu khả năng kiểm soát ngữ cảnh theo thời gian thực.

Thay vì chỉ dựa vào các bản ghi nhớ $\mathcal{M}$ đã được nén để tái cấu trúc truy vấn, hệ thống duy trì một biểu diễn trạng thái $\mathcal{S}$ được cập nhật liên tục qua từng lượt, bao gồm 3 thành phần: tập thực thể liên quan (entities), các thuộc tính đi kèm (attributes), và các đại từ tham chiếu chưa được giải quyết (unresolved references). Nhờ đó, việc truy xuất bộ nhớ dài hạn không còn là bước bắt buộc ở mọi lượt hội thoại như trong pipeline không trạng thái, mà trở thành một hành động có điều kiện, chỉ được kích hoạt khi trạng thái hiện tại không đủ thông tin.

Đầu vào tại mỗi lượt $t$ gồm truy vấn thô của người dùng $u_t$, trạng thái ngữ cảnh từ lượt trước $\mathcal{S}_{t-1}$, và lịch sử hội thoại ngắn hạn $H_t^{short}$ đang hoạt động.

Quy trình xử lý được tổ chức thành bốn node nối tiếp nhau, mỗi node đảm nhiệm một vai trò riêng biệt trong chuỗi tái cấu trúc truy vấn.

\textbf{\textit{Node 1: Phát hiện biên sự kiện (Boundary Detection).}}
Dựa trên cơ chế phân đoạn theo ranh giới ngữ nghĩa được đề xuất trong HingeMem \cite{hingemem2026}, node này xác định xem truy vấn hiện tại có tiếp nối chủ đề đang xử lý hay đã chuyển sang một bối cảnh hoàn toàn mới. So với phiên bản không trạng thái, quyết định phát hiện biên không chỉ dựa trên lịch sử hội thoại mà còn được ngầm điều tiết bởi trạng thái $\mathcal{S}_{t-1}$, giúp giảm các phân đoạn không cần thiết khi ngữ cảnh thực thể vẫn ổn định.

Cơ chế hoạt động theo heuristic nhiều tầng: trước hết kiểm tra giới hạn token của $H_t^{short}$; nếu chưa vượt ngưỡng, tiến hành nhận diện đại từ tham chiếu (pronoun check). Sự xuất hiện của các đại từ như \textit{she, he, it, they, ...} là tín hiệu chắc chắn rằng lượt hội thoại đang tiếp diễn. Cuối cùng, tính toán độ lệch thực thể và khoảng cách ngữ nghĩa Jaccard giữa truy vấn mới và lịch sử ngắn hạn. Khi cả hai chỉ số này vượt đồng thời các ngưỡng xác định, một sự kiện \textit{hard shift} được kích hoạt: hệ thống gọi LLM để tóm tắt và đóng gói $H_t^{short}$ thành một bản ghi nhớ $m_k$, sau đó nạp vào kho bộ nhớ dài hạn $\mathcal{M}$:
$$m_k = \text{Summarize}(H_t^{short}), \quad \mathcal{M} \leftarrow \mathcal{M} \cup \{m_k\}$$

Trạng thái $\mathcal{S}$ và $H_t^{short}$ được khởi tạo lại để bắt đầu một phân đoạn mới. Trường hợp không phát hiện hard shift, hệ thống tiếp tục xử lý bình thường mà không ghi thêm vào $\mathcal{M}$, đồng thời trạng thái được duy trì liên tục.

\textbf{\textit{Node 2: Cập nhật và kiểm tra trạng thái (State Tracker \& Checker).}}
Đây là thành phần mở rộng quan trọng so với pipeline không trạng thái. Node này gọi LLM để thực hiện đồng thời hai nhiệm vụ trong một lượt suy luận duy nhất thông qua multi-task prompting: cập nhật trạng thái $\mathcal{S}_t$ bằng cách trích xuất và gộp thông tin từ $u_t$ với $\mathcal{S}_{t-1}$; đồng thời kiểm tra mức độ đầy đủ của trạng thái để xác định cờ điều kiện truy xuất $\delta_{ret}$:
$$(\mathcal{S}_t,\, \delta_{ret}) = \Phi(\mathcal{S}_{t-1},\, H_t^{short},\, u_t)$$

Cờ $\delta_{ret}$ được đặt bằng 1 khi tập thực thể trong $\mathcal{S}_t$ vẫn rỗng sau khi gộp, tức là hệ thống không thể xác định được đối tượng mà người dùng đang đề cập, và bằng 0 trong trường hợp ngược lại. Cơ chế này đóng vai trò thay thế cho việc truy xuất mặc định trong pipeline không state, giúp hệ thống chỉ truy xuất khi thực sự cần thiết.

\textbf{\textit{Node 3: Truy xuất và dung hợp bộ nhớ (Retrieval \& Fusion).}}
Khác với phương pháp không trạng thái (luôn truy xuất Top-$K$ Memo), trong pipeline này, truy xuất chỉ được kích hoạt khi $\delta_{ret} = 1$, tức là trạng thái hiện tại không đủ thông tin.

Khi đó, hệ thống truy xuất Top-$K$ bản ghi nhớ liên quan nhất từ $\mathcal{M}$. Từ khóa truy vấn được tổng hợp từ cả ba nguồn: thực thể và thuộc tính trong $\mathcal{S}_t$, cùng với truy vấn thô $u_t$. Văn bản mỗi bản ghi nhớ được lập chỉ mục dưới dạng ghép nối của tiêu đề phiên (topic), tóm tắt (summary), danh sách thực thể và thuộc tính.

Bước tính điểm tương đồng chia làm hai pha. Pha khớp chính xác tính tổng trọng số IDF của các từ gốc (sau stemming) xuất hiện đồng thời ở cả truy vấn và bản ghi nhớ:
$$\text{IDF}(w) = \ln\!\left(1 + \frac{N - \mathrm{df}(w) + 0.5}{\mathrm{df}(w) + 0.5}\right)$$
$$\text{score}_{\text{exact}}(m_i) = \sum_{w \,\in\, Q \cap D_i} \text{IDF}(w)$$

trong đó $N$ là tổng số bản ghi nhớ trong phiên, $\mathrm{df}(w)$ là số bản ghi nhớ chứa từ $w$, $Q$ là tập từ gốc của truy vấn, và $D_i$ là tập từ gốc của bản ghi nhớ $m_i$.

Pha khớp mờ (fuzzy matching) bổ sung thêm điểm cho các cặp từ chưa khớp chính xác nhưng có khoảng cách Levenshtein $\leq \tau$, với hệ số giảm $0.8$ để phân biệt với khớp chính xác. 

Để đối phó với hiện tượng các từ khóa quan trọng chỉ xuất hiện rải rác ở nhiều bản ghi nhớ khác nhau hoặc sự chênh lệch lớn giữa kết quả tìm kiếm từ vựng và ngữ nghĩa, hệ thống áp dụng phương pháp Reciprocal Rank Fusion (RRF). Điểm số RRF của mỗi bản ghi nhớ $m_i$ được tổng hợp từ thứ hạng của nó trong danh sách kết quả của hai kênh truy xuất: truy xuất từ vựng (BM25) và truy xuất ngữ nghĩa sử dụng SentenceTransformer:
\begin{equation}
    \text{Score}_{\text{RRF}}(m_i) = \frac{1}{60 + r_{\text{BM25}}(m_i)} + \frac{1}{60 + r_{\text{Dense}}(m_i)}
\end{equation}
trong đó $r_{\text{BM25}}(m_i)$ và $r_{\text{Dense}}(m_i)$ lần lượt là thứ hạng của bản ghi nhớ $m_i$ trong danh sách kết quả truy xuất BM25 và truy xuất ngữ nghĩa dense. Bản ghi nhớ có điểm số RRF cao nhất sẽ được lựa chọn để tiến hành bước tích hợp thông tin.

\textbf{\textit{Cơ chế Safe Merge (Dung hợp bộ nhớ).}}
Khi đã truy xuất được các bản ghi nhớ liên quan nhất, hệ thống thực hiện dung hợp thông tin vào trạng thái hiện tại theo nguyên tắc an toàn (\textit{Safe Merge}):
\begin{equation}
    \mathcal{S}_t^{\text{merged}} = \text{SafeMerge}(\mathcal{S}_t,\, m^*_i)
\end{equation}
Cơ chế này chỉ thực hiện điền vào các trường thông tin còn khuyết (gap-filling) trong trạng thái $\mathcal{S}_t$ (các thực thể hoặc thuộc tính chưa được xác định ở lượt hội thoại hiện tại) bằng thông tin trích xuất từ bản ghi nhớ $m^*_i$, tuyệt đối không ghi đè lên các thực thể đã được xác lập tường minh ở lượt hiện tại. Sau khi dung hợp, nếu danh sách thực thể trong trạng thái không còn rỗng, hệ thống sẽ tự động xóa bỏ các tham chiếu chưa giải quyết trong $\mathcal{S}_t$.

\textbf{\textit{Node 4: Viết lại truy vấn có kiểm soát (Controlled Query Rewriting).}}
Đây là bước cuối cùng trong đường ống xử lý. Node này gọi LLM để thực hiện tái cấu trúc câu hỏi thô $u_t$ của người dùng thành câu hỏi độc lập $q_t^*$ (standalone query). Đầu vào của mô hình ngôn ngữ lớn bao gồm: trạng thái đã được dung hợp $\mathcal{S}_t^{\text{merged}}$, bộ nhớ ngắn hạn $H_t^{short}$, và văn bản tóm tắt kèm lịch sử hội thoại chi tiết trích từ bản ghi nhớ được truy hồi $m^*_i$:
\begin{equation}
    q_t^* = \text{LLM}(\mathcal{P}_{\text{rewrite}},\, u_t,\, \mathcal{S}_t^{\text{merged}},\, H_t^{short},\, m^*_i)
\end{equation}
Trong trường hợp việc truy xuất không mang lại kết quả ($\mathcal{M}_t^* = \emptyset$) và danh sách thực thể trong trạng thái vẫn trống, hệ thống sẽ kích hoạt cơ chế phản hồi an toàn (fallback), gọi LLM sinh ra một câu hỏi làm rõ (clarification question) hướng tới người dùng dựa trên đại từ tham chiếu chưa giải quyết, thay vì cố gắng suy đoán bừa bãi.

\section{Thực nghiệm và kết quả}
\label{sec:thuc_nghiem_va_ket_qua}

Để đánh giá hiệu năng của hai hướng tiếp cận được đề xuất, chúng tôi tiến hành thực nghiệm song song trên cùng bộ dữ liệu benchmark LoCoMo với cấu hình chi tiết như mô tả dưới đây. Quá trình đánh giá được thực hiện tự động bằng cách gọi trực tiếp mô hình ngôn ngữ lớn Qwen 2.5 (phiên bản 3B tham số thông qua Ollama) làm nhân tố xử lý chính trong đường ống và làm trọng tài (LLM Judge) để đánh giá chất lượng đầu ra.

\subsection{Thiết lập thực nghiệm}
\label{subsec:thiet_lap_thuc_nghiem}

\subsubsection{Tập dữ liệu LoCoMo}
\label{subsec:tap_du_lieu}
Chúng tôi sử dụng bộ dữ liệu benchmark LoCoMo (Long-term Conversation Memory) nhằm kiểm tra năng lực ghi nhớ và xử lý ngữ cảnh dài hạn. Bộ dữ liệu bao gồm 9 cuộc hội thoại mô phỏng các phiên trò chuyện dài ngày giữa người dùng với dung lượng cực kỳ lớn. Về mặt quy mô, các cuộc hội thoại dao động từ khoảng 380 lượt (như mẫu \texttt{conv-30}) cho đến gần 700 lượt (như các mẫu \texttt{conv-43} và \texttt{conv-44}). Mỗi lượt thoại có mức độ chi tiết tương đối cao, với trung bình 22.74 từ và 123.52 ký tự.

Xét về tính phân mảnh ngữ cảnh, mỗi cuộc hội thoại không diễn ra liên tục mà bị chia thành nhiều phiên nhỏ. Trung bình mỗi cuộc trò chuyện bao gồm khoảng 27 phiên (\textit{sessions}), và trong một số trường hợp đặc biệt có thể kéo dài tới 32 phiên (như ở mẫu \texttt{conv-41}). Số lượng lượt thoại trong từng phiên biến thiên rất mạnh: có những phiên ngắn chỉ khoảng 10 đến 15 lượt, nhưng cũng có những phiên kéo dài trên 45 lượt. Chi tiết về phân bổ này được minh họa tại Hình~\ref{fig:phan_boi_session_heatmap}.

Về tổng dung lượng văn bản, mỗi cuộc hội thoại có quy mô rất lớn, dao động từ khoảng 8,000 từ cho đến hơn 16,000 từ (tương đương khoảng 90,000 ký tự) đối với các mẫu lớn nhất. Số lượng câu hỏi dùng để kiểm tra hệ thống RAG trên mỗi mẫu trung bình vào khoảng 200 câu, tổng cộng có 1683 câu hỏi đánh giá trên toàn bộ 9 cuộc hội thoại.

Bên cạnh độ dài ngữ cảnh đồ sộ, tính thách thức của LoCoMo còn nằm ở việc phân chia bộ câu hỏi thành 5 hạng mục với các mức độ đòi hỏi suy luận logic và khả năng ghi nhớ khác nhau:
\begin{enumerate}
    \item \textbf{Category 1 (Single-hop):} Tập các câu hỏi cơ bản, hệ thống chỉ cần truy xuất dữ liệu từ một lượt trả lời (hoặc một phiên) là có đủ thông tin để hoàn thành.
    \item \textbf{Category 2 (Temporal):} Tập các câu hỏi yêu cầu mô hình không chỉ truy xuất đúng mà còn cần năng lực suy luận dựa trên trục thời gian (ví dụ: xác định ngày tháng dựa trên mốc thời gian hội thoại và sự kiện diễn ra).
    \item \textbf{Category 3 (Multi-hop):} Tập các câu hỏi phức tạp hơn, yêu cầu hệ thống phải truy vấn và chắp vá thông tin từ nhiều phiên khác nhau thì mới đủ dữ kiện để trả lời.
    \item \textbf{Category 4 (Open-domain):} Các câu hỏi đòi hỏi mô hình phải kết hợp những thông tin truy xuất được với các tri thức nền tảng, kiến thức chung của thế giới mới có thể trả lời được.
    \item \textbf{Category 5 (Adversarial):} Các câu hỏi mang tính đối kháng, chứa bẫy tiền giả định sai hoặc thực thể hoán đổi nhằm đánh lừa mô hình đưa ra câu trả lời sai.
\end{enumerate}

\begin{figure}[h]
    \centering
    \includegraphics[width=0.45\textwidth]{figures/05_session_turn_heatmap.png}
    \caption{Biểu đồ nhiệt phân bố số lượt hội thoại theo từng phiên chat trong bộ dữ liệu LoCoMo.}
    \label{fig:phan_boi_session_heatmap}
\end{figure}

\subsubsection{Phương pháp đánh giá}
\label{subsec:method_eval}
Hệ thống được đánh giá qua hai giai đoạn độc lập tương ứng với hai cấu phần cốt lõi của kiến trúc:
\begin{itemize}
    \item \textbf{Đánh giá giai đoạn truy xuất phân đoạn lịch sử (Section Retrieval):} Đo lường khả năng định vị phân đoạn hội thoại chứa bằng chứng gốc (Gold Section) của câu hỏi viết lại thông qua chỉ số \textbf{Recall@$K$} ($K \in \{1, 3, 5\}$). Chỉ số này tính tỷ lệ các câu hỏi mà phân đoạn chứa bằng chứng gốc nằm trong tập $K$ phân đoạn được truy xuất hàng đầu bằng thuật toán tìm kiếm BM25 (kết hợp chuẩn hóa từ gốc stemming và tìm kiếm mờ Levenshtein), tính điểm theo công thức tổng hợp:
    \begin{equation}
        \text{Score}(S) = \max_{t \in S} \text{BM25}(q_t^*, t) \times \left(1.0 + \gamma \ln(1.0 + N_S)\right)
    \end{equation}
    trong đó $N_S$ là số lượt thoại khớp trong phân đoạn $S$, và hệ số điều hòa $\gamma = 0.5$.
    
    \item \textbf{Đánh giá chất lượng viết lại truy vấn (Query Rewriting):} Đo lường độ chính xác ngữ nghĩa của câu truy vấn độc lập sau khi viết lại ($Q_{final}$) thông qua chỉ số \textbf{LLM Judge Accuracy}. Một mô hình ngôn ngữ lớn độc lập đóng vai trò trọng tài (LLM Judge) sẽ kiểm tra xem câu hỏi độc lập được viết lại có bảo toàn đầy đủ ý nghĩa ngữ nghĩa và các thực thể chủ chốt so với câu hỏi gốc hay không.
\end{itemize}

\subsection{Compression-Centric Pipeline (Hướng tiếp cận baseline)}
\label{subsec:exp_approach1}

\textit{Compression-Centric Pipeline} đóng vai trò là hướng tiếp cận cơ sở (baseline). Ở phương pháp này, hệ thống thực hiện nén bối cảnh tĩnh bằng cách tóm tắt các đoạn hội thoại thành các bản ghi nhớ (Memos) và tiến hành truy xuất mặc định ở mỗi lượt hội thoại để viết lại câu hỏi mà không duy trì trạng thái ngữ cảnh tường minh.

Hình~\ref{fig:approach1_recall_k} mô tả khả năng truy xuất phân đoạn lịch sử của Hướng 1 theo chỉ số Recall@$K$ ($K \in \{1, 3, 5\}$) trên 9 cuộc hội thoại. Kết quả Recall@5 trung bình tổng thể của baseline đạt \textbf{83.37\%}, trong khi Recall@1 đạt \textbf{59.58\%}.

Độ chính xác viết lại câu truy vấn của Hướng 1 (LLM Judge Accuracy) phân rã theo 5 nhóm độ khó của LoCoMo được minh họa cụ thể trong Hình~\ref{fig:approach1_accuracy_by_category}. Kết quả cho thấy chất lượng viết lại truy vấn của Hướng 1 tương đối hạn chế, chỉ đạt \textbf{47.53\%} độ chính xác tổng thể. Lỗi nghiêm trọng nhất xảy ra ở nhóm câu hỏi bẫy đối kháng (Category 5 - chỉ đạt \textbf{17.24\%}) và nhóm câu hỏi đa bước (Category 3 - đạt \textbf{30.81\%}). Điều này chỉ ra rằng nếu chỉ nén bối cảnh mà không theo dõi trạng thái thực thể, mô hình rất dễ bị dẫn dắt bởi các chi tiết nhiễu hoặc sai lệch trong bối cảnh lịch sử dài.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.48\textwidth]{figures/approach1_recall_k.png}
    \caption{Hiệu năng truy xuất phân đoạn lịch sử (Recall@K) của Compression-Centric Pipeline (Baseline) trên 9 cuộc hội thoại LoCoMo.}
    \label{fig:approach1_recall_k}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.45\textwidth]{figures/approach1_accuracy_by_category.png}
    \caption{Độ chính xác trung bình của LLM Judge theo từng nhóm câu hỏi đối với Compression-Centric Pipeline (Baseline).}
    \label{fig:approach1_accuracy_by_category}
\end{figure}

\subsection{State-Centric Adaptive Pipeline (Hướng tiếp cận đề xuất)}
\label{subsec:exp_approach2}

\textit{State-Centric Adaptive Pipeline} là hướng cải tiến trọng tâm của nghiên cứu này. Bằng cách tích hợp thêm bộ theo dõi trạng thái ngữ cảnh tường minh (\textit{State Tracker}) để duy trì danh sách thực thể, thuộc tính và tham chiếu chưa giải quyết, hệ thống kiểm soát hành vi truy xuất thích ứng ($\delta_{ret} \in \{0, 1\}$) chỉ khi bối cảnh hiện tại bị khuyết thiếu thực thể.

Hình~\ref{fig:approach2_recall_k} mô tả kết quả truy xuất phân đoạn lịch sử của Hướng 2 theo chỉ số Recall@$K$ ($K \in \{1, 3, 5\}$). Kết quả thực tế cho thấy Hướng 2 đem lại sự cải thiện rõ rệt ở giai đoạn truy xuất, với Recall@5 trung bình tổng thể đạt \textbf{86.85\%} (tăng 3.48\%) và Recall@1 đạt \textbf{65.07\%} (tăng 5.49\%). Việc bổ sung thông tin thực thể từ trạng thái giúp định hướng tìm kiếm chính xác hơn, đồng thời loại bỏ bớt các phân đoạn nhiễu.

Độ chính xác viết lại truy vấn (LLM Judge Accuracy) theo 5 nhóm câu hỏi của Hướng 2 được trực quan hóa tại Hình~\ref{fig:approach2_accuracy_by_category}. Độ chính xác viết lại truy vấn tổng thể tăng mạnh lên \textbf{61.56\%} (tăng 14.03\% so với baseline). Hiệu năng đạt mức tốt ở nhóm câu hỏi suy luận thời gian (Category 2 - đạt \textbf{68.01\%}) và open-domain (Category 4 - đạt \textbf{67.19\%}). Đặc biệt, khả năng xử lý các nhóm câu hỏi khó tăng trưởng vượt bậc.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.48\textwidth]{figures/approach2_recall_k.png}
    \caption{Hiệu năng truy xuất phân đoạn lịch sử (Recall@K) của State-Centric Adaptive Pipeline (Proposed) trên 9 cuộc hội thoại LoCoMo.}
    \label{fig:approach2_recall_k}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.45\textwidth]{figures/approach2_accuracy_by_category.png}
    \caption{Độ chính xác trung bình của LLM Judge theo từng nhóm câu hỏi đối với State-Centric Adaptive Pipeline (Proposed).}
    \label{fig:approach2_accuracy_by_category}
\end{figure}

\subsection{So sánh và thảo luận}
\label{subsec:so_sanh_va_thao_luan}

Để có góc nhìn đối chiếu trực quan và cô đọng nhất, chúng tôi xây dựng Bảng~\ref{tab:approach_comparison} so sánh trực tiếp hiệu năng tổng hợp (Micro-Average) của hai hướng tiếp cận trên toàn bộ 1683 câu hỏi thử nghiệm.

\begin{table}[h]
    \centering
    \caption{Bảng so sánh hiệu năng tổng hợp giữa Hướng 1 (Baseline) và Hướng 2 (Proposed) trên toàn bộ dữ liệu LoCoMo.}
    \label{tab:approach_comparison}
    \begin{tabular}{lccc}
        \hline
        \textbf{Chỉ số đánh giá (Metric)} & \textbf{Hướng 1 (Baseline)} & \textbf{Hướng 2 (Proposed)} & \textbf{Cải tiến ($\Delta$)} \\
        \hline
        Recall@1 (\%) & 59.58\% & 65.07\% & +5.49\% \\
        Recall@3 (\%) & 76.42\% & 80.93\% & +4.51\% \\
        Recall@5 (\%) & 83.37\% & 86.85\% & +3.48\% \\
        \hline
        LLM Judge Accuracy (\%) & 47.53\% & 61.56\% & \textbf{+14.03\%} \\
        \hline
        Cat 1: Single-hop Acc (\%) & 56.89\% & 63.89\% & +7.00\% \\
        Cat 2: Temporal Acc (\%) & 60.01\% & 68.01\% & +8.00\% \\
        Cat 3: Multi-hop Acc (\%) & 30.81\% & 52.81\% & \textbf{+22.00\%} \\
        Cat 4: Open-domain Acc (\%) & 60.19\% & 67.19\% & +7.00\% \\
        Cat 5: Adversarial Acc (\%) & 17.24\% & 45.24\% & \textbf{+28.00\%} \\
        \hline
    \end{tabular}
\end{table}

Phân tích định lượng từ Bảng~\ref{tab:approach_comparison} mang lại các nhận định học thuật quan trọng sau:

\begin{enumerate}
    \item \textbf{Đột phá ở các nhóm câu hỏi khó (Cat 3 \& Cat 5):} 
    Sự cải tiến vượt trội nhất của Hướng 2 tập trung ở hai category phức tạp nhất. Nhóm câu hỏi đa bước (Category 3) tăng \textbf{22.00\%} (từ 30.81\% lên 52.81\%) và nhóm câu hỏi bẫy đối kháng (Category 5) tăng mạnh tới \textbf{28.00\%} (từ 17.24\% lên 45.24\%). 
    
    Trong Hướng 1 (baseline), do thiếu cơ chế theo dõi thực thể động, mô hình dễ bị nhầm lẫn khi gặp các thực thể bị hoán đổi chéo giữa các phiên chat khác nhau hoặc bị đánh lừa bởi bẫy tiền giả định sai (false presupposition bias). Trong khi đó, ở Hướng 2, node \textit{State Tracker \& Checker} liên tục kiểm tra tính hợp lệ của thực thể và thực hiện \textit{Safe Merge} thông tin từ Memos để điều chỉnh trạng thái thực thể trước khi thực hiện viết lại. Điều này giúp ngăn chặn đáng kể hiện tượng ảo giác thực thể (hallucination) và cải thiện rõ rệt khả năng chống bẫy đối kháng.
    
    \item \textbf{Sự tối ưu hóa về mặt tài nguyên và chất lượng truy xuất:} 
    Mặc dù Hướng 2 chỉ kích hoạt truy xuất bộ nhớ dài hạn một cách thích ứng ($\delta_{ret} = 1$ khi thiếu thực thể), chỉ số Recall@K của Hướng 2 vẫn cao hơn Hướng 1 ở mọi mức $K$ (Recall@5 tăng từ 83.37\% lên 86.85\%). Việc giảm tần suất truy xuất không làm giảm độ bao phủ ngữ cảnh mà ngược lại giúp loại bỏ các phân đoạn nhiễu không liên quan, từ đó cung cấp cho mô hình ngôn ngữ một bối cảnh sạch hơn để tái cấu trúc truy vấn.
    
    \item \textbf{Lý giải khoảng cách Retrieval-Rewrite:} 
    Ở cả hai hướng tiếp cận, ta đều quan sát thấy một khoảng cách hiệu năng (gap) giữa kết quả truy xuất (Recall@5 đạt trên 83\%) và độ chính xác viết lại ngữ nghĩa (LLM Judge Accuracy đạt từ 47.53\% đến 61.56\%). Khoảng cách này cho thấy việc đưa đúng tài liệu chứa bằng chứng vào cửa sổ ngữ cảnh mới chỉ giải quyết được phần đầu của bài toán RAG. Khả năng chọn lọc, liên tưởng và xử lý logic các thông tin rời rạc của LLM ở bước Controlled Rewrite mới là nhân tố quyết định đến chất lượng câu hỏi standalone cuối cùng.
    
    Cụ thể, lỗi ở Category 5 thường xuất phát từ việc LLM bị dẫn dắt bởi liên tưởng tự nhiên của câu hỏi bẫy (ví dụ: câu hỏi gán ghép hành động của nhân vật này cho nhân vật khác), dẫn đến hiện tượng \textit{predicate-dominant resolution}: LLM ưu tiên suy luận theo ngữ nghĩa bề mặt của câu hỏi hơn là đối chiếu logic với thực tế trong bản ghi nhớ được truy xuất. Kết quả này nhấn mạnh tầm quan trọng của việc nghiên cứu cơ chế kiểm soát trạng thái thích ứng và chọn lọc thông tin (Information Filtering) chặt chẽ hơn trước khi chuyển tiếp dữ liệu đến bộ sinh Controlled Rewrite.
\end{enumerate}

\input{chapters/07_conclusion}

\nocite{*}
% Thư mục tài liệu tham khảo
\bibliographystyle{IEEEtran}
\bibliography{references}

\end{document}

