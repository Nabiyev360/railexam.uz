document.addEventListener("DOMContentLoaded", () => {
    const video = document.getElementById("video");
    const captureButton = document.getElementById("capture");
    const pin = document.getElementById("pin");

    // Start the webcam
    navigator.mediaDevices
        .getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(err => {
            console.error("Error accessing the camera: ", err);
            alert("Kamerani ishga tushirib bo'lmadi. Iltimos, ruxsat bering.");
        });

    // Capture a frame and send it to the server
    captureButton.addEventListener("click", event => {
        event.preventDefault();

        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext("2d");
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob(blob => {
            const formData = new FormData();
            formData.append("frame", blob);
            formData.append("pin", pin.value);

            fetch("/profiles/login/employee/", {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === "success") {
//                        alert("Tizimga muvaffaqiyatli kirdingiz!");
                        window.location.href = data.redirect_url; // Redirect after successful login
                    } else {
                        alert(data.message || "Tizimga kirish muvaffaqiyatsiz bo'ldi.");
                    }
                })
                .catch(err => {
                    console.error("Error:", err);
                    alert("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.");
                });
        }, "image/jpeg");
    });
});
