// Curated from the topics in https://www.mathvn.com/2021/09/latex-co-ban-cach-go-cac-cong-thuc-ki.html
// Entries are editable examples, not copied article text. KaTeX-compatible syntax is used.
window.LATEX_CATALOG = [
  {name: 'Mũ, chỉ số & phép tính', items: [
    ['Số mũ', String.raw`x^n`], ['Chỉ số dưới', String.raw`x_1`],
    ['Mũ và chỉ số', String.raw`C_5^3`], ['Phân số', String.raw`\frac{a}{b}`],
    ['Phân số lớn', String.raw`\dfrac{a}{b}`], ['Căn bậc hai', String.raw`\sqrt{x}`],
    ['Căn bậc n', String.raw`\sqrt[n]{x}`], ['Ngoặc tự giãn', String.raw`\left(\frac{a}{b}\right)^2`],
    ['Tổ hợp', String.raw`\binom{n}{k}`], ['Nhân', String.raw`a\times b`],
    ['Chia hết', String.raw`a\mid b`], ['Cộng trừ', String.raw`\pm`],
    ['Tích vô hướng', String.raw`\vec{a}\cdot\vec{b}`],
    ['Tích trong', String.raw`\langle x,y\rangle`]
  ]},
  {name: 'So sánh, quan hệ & dấu chấm', items: [
    ['Bé hơn', String.raw`a\lt b`], ['Lớn hơn', String.raw`a\gt b`],
    ['Lớn hơn hoặc bằng', String.raw`a\ge b`], ['≥ dạng cong', String.raw`a\geqslant b`],
    ['Bé hơn hoặc bằng', String.raw`a\le b`], ['≤ dạng cong', String.raw`a\leqslant b`],
    ['Khác', String.raw`a\ne b`], ['Đồng nhất', String.raw`a\equiv b`],
    ['Xấp xỉ', String.raw`a\approx b`], ['Đồng dạng', String.raw`A\sim B`],
    ['Đồng dạng ngược', String.raw`A\backsim B`],
    ['Tổng trực tiếp', String.raw`A\oplus B`], ['Tích tensor', String.raw`A\otimes B`],
    ['Chấm giữa', String.raw`a\cdots z`], ['Chấm thấp', String.raw`a\ldots z`],
    ['Chấm dọc', String.raw`\vdots`], ['Chấm chéo', String.raw`\ddots`]
  ]},
  {name: 'Suy luận & logic', items: [
    ['Suy ra', String.raw`A\Rightarrow B`], ['Mũi tên phải', String.raw`A\rightarrow B`],
    ['Mũi tên trái', String.raw`A\Leftarrow B`], ['Tương đương', String.raw`A\Leftrightarrow B`],
    ['Hai chiều', String.raw`A\leftrightarrow B`], ['Khi và chỉ khi', String.raw`A\iff B`],
    ['Hoặc', String.raw`A\vee B`], ['Và', String.raw`A\wedge B`],
    ['Bởi vì', String.raw`\because`], ['Vì vậy', String.raw`\therefore`]
  ]},
  {name: 'Giải tích & dãy số', items: [
    ['Vô cực', String.raw`\infty`], ['Giới hạn', String.raw`\lim_{x\to\infty}f(x)`],
    ['Giới hạn một phía', String.raw`\lim_{x\to 0^+}f(x)`],
    ['Tích phân', String.raw`\int f(x)\,dx`], ['Tích phân xác định', String.raw`\int_0^1 f(x)\,dx`],
    ['Tích phân kép', String.raw`\iint_D f(x,y)\,dx\,dy`],
    ['Tích phân bội ba', String.raw`\iiint_V f\,dV`],
    ['Tích phân đường', String.raw`\oint_C f\,ds`],
    ['Vạch lấy giá trị', String.raw`\left. F(x)\right|_0^1`],
    ['Tổng sigma', String.raw`\sum_{n=1}^{\infty}\frac{1}{n^2}`],
    ['Tích pi', String.raw`\prod_{n=1}^{N}n`],
    ['Đạo hàm', String.raw`f'(x)`], ['Đạo hàm phân số', String.raw`\frac{dy}{dx}`]
  ]},
  {name: 'Hệ, ma trận & trình bày', items: [
    ['Hệ phương trình', String.raw`\begin{cases}x+y=5\\x-y=3\end{cases}`, true],
    ['Tuyển (ngoặc vuông)', String.raw`\left[\begin{array}{l}x-1=0\\x^3+x=0\end{array}\right.`, true],
    ['Ma trận', String.raw`\begin{bmatrix}1&2&3\\4&5&6\end{bmatrix}`, true],
    ['Định thức', String.raw`\begin{vmatrix}1&2\\3&4\end{vmatrix}`, true],
    ['Các bước biến đổi', String.raw`\begin{aligned}A&=a+b\\&=c+d\end{aligned}`, true],
    ['Mảng nhiều dòng', String.raw`\begin{array}{l}a+b=c\\x+y=z\end{array}`, true],
    ['Bảng số liệu', String.raw`\begin{array}{|c|c|c|}\hline x&1&2\\\hline y&3&4\\\hline\end{array}`, true],
    ['Bảng biến thiên', String.raw`\begin{array}{c|ccccc}x&-\infty&&0&&+\infty\\\hline f'(x)&&+&0&- &\\\hline f(x)&&\nearrow&1&\searrow&\end{array}`, true],
    ['Đóng khung kết quả', String.raw`\boxed{x=81}`],
    ['Ngoặc nhọn nhiều phần', String.raw`\left\{\begin{array}{l}x>0\\y<1\end{array}\right.`, true]
  ]},
  {name: 'Tập hợp', items: [
    ['Thuộc', String.raw`x\in A`], ['Không thuộc', String.raw`x\notin A`],
    ['Tập con', String.raw`A\subset B`], ['Không là tập con', String.raw`A\not\subset B`],
    ['Hợp', String.raw`A\cup B`], ['Giao', String.raw`A\cap B`],
    ['Hợp nhiều tập', String.raw`\bigcup_{k=1}^n A_k`],
    ['Giao nhiều tập', String.raw`\bigcap_{k=1}^n A_k`],
    ['Tập liệt kê', String.raw`S=\{1,2,3\}`],
    ['Tập rỗng', String.raw`\emptyset`], ['Tập rỗng dạng khác', String.raw`\varnothing`],
    ['Tập số tự nhiên', String.raw`\mathbb{N}`], ['Tập số nguyên', String.raw`\mathbb{Z}`],
    ['Tập số hữu tỉ', String.raw`\mathbb{Q}`], ['Tập số thực', String.raw`\mathbb{R}`],
    ['Tập số phức', String.raw`\mathbb{C}`]
  ]},
  {name: 'Hàm, chữ cái & trang trí', items: [
    ['Sin', String.raw`\sin x`], ['Cos', String.raw`\cos x`],
    ['Tan', String.raw`\tan x`], ['Cot', String.raw`\cot x`],
    ['Arcsin', String.raw`\arcsin x`],
    ['Logarit', String.raw`\log_2 x`], ['Log tự nhiên', String.raw`\ln x`],
    ['Biến cố đối', String.raw`\bar{A}`],
    ['Chữ Hy Lạp thường', String.raw`\alpha,\beta,\gamma,\delta,\epsilon,\lambda,\pi,\phi,\varphi`],
    ['Chữ Hy Lạp hoa', String.raw`\Gamma,\Delta,\Omega,\Pi,\Phi,\Sigma`],
    ['Chữ thư pháp', String.raw`\mathcal{A}`],
    ['Khoảng trắng vừa', String.raw`a\quad b`], ['Khoảng trắng rộng', String.raw`a\qquad b`],
    ['Ghi chú dưới', String.raw`\underset{n\text{ lần}}{\underbrace{a\cdot a\cdots a}}`],
    ['Chữ LaTeX', String.raw`\LaTeX`]
  ]},
  {name: 'Hình học & vectơ', items: [
    ['Góc', String.raw`\angle ABC`], ['Góc có mũ', String.raw`\widehat{ABC}`],
    ['Góc đo', String.raw`\measuredangle ABC`], ['Góc cầu', String.raw`\sphericalangle ABC`],
    ['Độ', String.raw`45^\circ`], ['Tam giác', String.raw`\triangle ABC`],
    ['Tam giác lớn', String.raw`\bigtriangleup ABC`],
    ['Hình vuông', String.raw`\square`], ['Hình tròn', String.raw`\bigcirc`],
    ['Vuông góc', String.raw`AB\bot CD`], ['Song song', String.raw`AB\parallel CD`],
    ['Cung tròn', String.raw`\overset{\frown}{AB}`],
    ['Cung lượng giác', String.raw`\overset{\curvearrowright}{AB}`],
    ['Vectơ', String.raw`\vec{a}`], ['Vectơ hai điểm', String.raw`\overrightarrow{AB}`],
    ['Độ dài đại số', String.raw`\overline{AB}`]
  ]}
];
