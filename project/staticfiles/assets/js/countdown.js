"use strict";
// Countdown js
const second = 1000,
    minute = second * 60,
    hour = minute * 60,
    day = hour * 24;

const examId = document.getElementById("exam_id").textContent.trim();

fetch(`/exams/get-deadline/${examId}`)
  .then(response => response.json())
  .then(data => {
    if (data.server_now && data.deadline) {
      // Parse the `deadline` from the API response and calculate the initial distance
      var serverNow = new Date(data.server_now).getTime();
      const deadline = new Date(data.deadline).getTime();
      let distance = deadline - serverNow; // Initial distance in milliseconds

      // Start the countdown
      let x = setInterval(function () {
        if (distance <= 0) {
          clearInterval(x);
          document.getElementById('minutes').innerText = "0";
          document.getElementById('seconds').innerText = "0";
          // Automatically click the button with ID "exam_end_button"
          document.getElementById('exam_end_button').click();
        } else {
          // Update the distance manually (decrease by 1 second)
          distance -= second;

          // Update the timer display
          document.getElementById('minutes').innerText = Math.floor((distance % (hour)) / (minute));
          document.getElementById('seconds').innerText = Math.floor((distance % (minute)) / second);
        }
      }, second);
    } else {
      console.error("Invalid response: started or deadline is missing");
      alert("Failed to load the deadline.");
    }
  })
  .catch(error => {
    console.error("Error fetching deadline:", error);
    alert("Failed to load the deadline.");
  });