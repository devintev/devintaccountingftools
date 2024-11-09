document.addEventListener('DOMContentLoaded', function() {
    window.submitForm = function(pageName) {
        var logLevelValue = document.getElementById('logLevel').value; // Get the current value of the slider
        console.log("Submitting form with log level:", logLevelValue); 
        document.getElementById('navInput').value = pageName;
        document.getElementById('navForm').submit();
    };
    
    // This function is called whenever the slider value changes
    function updateLogLevelLabel() {
        var slider = document.getElementById('logLevel');
        var hidden_slider = document.getElementById('logLevel2');
        hidden_slider.value = slider.value;
        var display = document.getElementById('logLevelDisplay');
        var logLevels = ['critical', 'error', 'warning', 'info', 'debug']; // Log levels corresponding to slider values 0-4
        display.innerText = logLevels[slider.value]; // Update the display text based on the slider value
    }

    // Add an event listener to the slider to call the update function on change
    var slider = document.getElementById('logLevel');
    if (slider) { // Check if the slider exists to avoid null reference errors
        slider.addEventListener('input', updateLogLevelLabel);

        // Initialize the display for the default value
        updateLogLevelLabel();
    }

    var tooltipContainers = document.querySelectorAll('.tooltip-container');
    var timeoutId;

    tooltipContainers.forEach(function(container) {
        var tooltipContent = container.querySelector('.tooltip-content');

        container.addEventListener('mouseenter', function() {
            timeoutId = setTimeout(function() {
                tooltipContent.style.display = 'block';
            }, 800);
        });

        container.addEventListener('mouseleave', function() {
            clearTimeout(timeoutId);
            tooltipContent.style.display = 'none';
        });

        tooltipContent.addEventListener('mouseenter', function() {
            clearTimeout(timeoutId);
        });

        tooltipContent.addEventListener('mouseleave', function() {
            tooltipContent.style.display = 'none';
        });
    });
    const checkbox = document.getElementById('parsing-messages-visible');
    const messageBox = document.getElementById('message-box');

    checkbox.addEventListener('change', (event) => {
        if (checkbox.checked) {
            messageBox.style.display = 'block';
        } else {
            messageBox.style.display = 'none';
        }
    });

});