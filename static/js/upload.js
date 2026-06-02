document.addEventListener('DOMContentLoaded', () => {
    // app.js에서 지원해야 하지만 여기서는 로컬하게 작성.
    console.log("Upload JS initialized");
});

// 업로드 로직 간략화
async function doUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/upload/', {
        method: 'POST',
        body: formData
    });
    const data = await res.json();
    return data;
}

// 간단한 이벤트 바인딩
const fileInput = document.getElementById('fileInput');
if (fileInput) {
    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            const res = await doUpload(file);
            if(res.success) {
                alert("업로드 성공! Session ID: " + res.data.session_id);
                // 실 서비스에서는 여기서 미리보기 로드 로직
            }
        }
    });
}
