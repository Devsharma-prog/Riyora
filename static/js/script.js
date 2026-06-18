document.addEventListener("DOMContentLoaded", function () {
    // -------------------------
    // Helper: Dynamic Toast System (Never use browser alert)
    // -------------------------
    const toastContainer = document.getElementById("toastContainer");

    function showToast(message, type = "info") {
        if (!toastContainer) return;
        const toast = document.createElement("div");
        toast.className = `toast-custom ${type}`;
        
        let prefix = "ℹ️ ";
        if (type === "success") prefix = "✅ ";
        if (type === "danger") prefix = "❌ ";
        if (type === "warning") prefix = "⚠️ ";

        toast.innerHTML = `
            <span class="toast-message">${prefix}${message}</span>
            <button type="button" class="toast-close-btn" aria-label="Close message">&times;</button>
        `;

        toastContainer.appendChild(toast);

        // Auto remove
        const autoRemove = setTimeout(() => {
            removeToast(toast);
        }, 4000);

        // Close on button click
        toast.querySelector(".toast-close-btn").addEventListener("click", () => {
            clearTimeout(autoRemove);
            removeToast(toast);
        });
    }

    function removeToast(toast) {
        toast.classList.add("fade-out");
        toast.addEventListener("animationend", () => {
            toast.remove();
        });
    }

    // Expose toast globally for template triggers
    window.showToast = showToast;

    // -------------------------
    // Helper: getCSRFToken
    // -------------------------
    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    // -------------------------
    // 1. Fullscreen Disclaimer Modal
    // -------------------------
    const disclaimerOverlay = document.getElementById("disclaimerOverlay");
    const continueBtn = document.getElementById("continueDisclaimerBtn");
    const exitBtn = document.getElementById("exitDisclaimerBtn");

    if (disclaimerOverlay) {
        const accepted = localStorage.getItem("riyora_disclaimer_accepted");
        if (!accepted) {
            disclaimerOverlay.style.setProperty("display", "flex", "important");
        } else {
            disclaimerOverlay.style.setProperty("display", "none", "important");
        }
    }

    if (continueBtn && disclaimerOverlay) {
        continueBtn.addEventListener("click", function () {
            localStorage.setItem("riyora_disclaimer_accepted", "true");
            disclaimerOverlay.style.setProperty("display", "none", "important");
            showToast("Disclaimer accepted. Welcome to Riyora!", "success");
        });
    }

    if (exitBtn) {
        exitBtn.addEventListener("click", function () {
            window.location.href = "https://www.google.com";
        });
    }

    // -------------------------
    // 2. Session Inactivity Tracker (15 mins client sync)
    // -------------------------
    let idleTime = 0;
    const sessionExpiredOverlay = document.getElementById("sessionExpiredOverlay");

    function resetIdleTimer() {
        idleTime = 0;
    }

    // Track user inputs to reset idle timer
    document.onmousemove = resetIdleTimer;
    document.onkeypress = resetIdleTimer;
    document.ontouchstart = resetIdleTimer;

    // Increment idle counter every minute
    const idleInterval = setInterval(() => {
        idleTime++;
        if (idleTime >= 15) { // 15 Minutes
            showSessionExpiredModal();
        }
    }, 60000);

    function showSessionExpiredModal() {
        clearInterval(idleInterval);
        if (sessionExpiredOverlay) {
            sessionExpiredOverlay.style.setProperty("display", "flex", "important");
        } else {
            showToast("Your session has expired due to inactivity. Please reload.", "danger");
        }
    }

    // -------------------------
    // 3. Dark/Light Theme Switcher
    // -------------------------
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const sunIcon = document.getElementById("themeSunIcon");
    const moonIcon = document.getElementById("themeMoonIcon");

    const savedTheme = localStorage.getItem("riyora_theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcons(savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", function () {
            const currentTheme = document.documentElement.getAttribute("data-theme");
            const newTheme = currentTheme === "light" ? "dark" : "light";
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("riyora_theme", newTheme);
            updateThemeIcons(newTheme);
            showToast(`Theme changed to ${newTheme} mode`, "success");

            // Telemetry tracking
            fetch('/track_theme_toggle', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).catch(err => console.error("Telemetry failed:", err));
        });
    }

    function updateThemeIcons(theme) {
        if (!sunIcon || !moonIcon) return;
        if (theme === "light") {
            sunIcon.style.display = "none";
            moonIcon.style.display = "inline-block";
        } else {
            sunIcon.style.display = "inline-block";
            moonIcon.style.display = "none";
        }
    }

    // -------------------------
    // 4. UPI ID Clipboard Copy & Telemetry Tracker
    // -------------------------
    const copyUpiBtn = document.getElementById("copyUpiBtn");
    const upiIdText = document.getElementById("upiIdText");

    if (copyUpiBtn && upiIdText) {
        copyUpiBtn.addEventListener("click", function () {
            const upiId = upiIdText.textContent.trim();
            navigator.clipboard.writeText(upiId).then(() => {
                const originalText = copyUpiBtn.textContent;
                copyUpiBtn.textContent = "Copied!";
                copyUpiBtn.classList.add("copied");
                showToast("UPI ID copied to clipboard!", "success");
                setTimeout(() => {
                    copyUpiBtn.textContent = originalText;
                    copyUpiBtn.classList.remove("copied");
                }, 2000);
            }).catch(err => {
                console.error("Failed to copy UPI ID: ", err);
                showToast("Failed to copy UPI ID. Please copy manually.", "danger");
            });

            // Telemetry tracking
            fetch('/track_support_click', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).catch(err => console.error("Telemetry failed:", err));
        });
    }

    // PayPal support button telemetry tracking
    const paypalSupportBtn = document.getElementById("paypalSupportBtn");
    if (paypalSupportBtn) {
        paypalSupportBtn.addEventListener("click", function () {
            fetch('/track_support_click', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).catch(err => console.error("Telemetry failed:", err));
        });
    }

    // -------------------------
    // 5. Payment Loading Screen Helpers
    // -------------------------
    const loadingOverlay = document.getElementById("loadingOverlay");

    function showLoadingOverlay(message = "Processing Payment...") {
        if (loadingOverlay) {
            const messageEl = document.getElementById("loadingMessage");
            if (messageEl) messageEl.textContent = message;
            loadingOverlay.style.setProperty("display", "flex", "important");
        }
    }

    function hideLoadingOverlay() {
        if (loadingOverlay) {
            loadingOverlay.style.setProperty("display", "none", "important");
        }
    }

    // -------------------------
    // 6. PayPal Buttons Integration
    // -------------------------
    const paypalContainer = document.getElementById("paypal-button-container");
    if (paypalContainer && typeof paypal !== "undefined") {
        const csrfToken = getCSRFToken();

        paypal.Buttons({
            createOrder: function () {
                showLoadingOverlay("Initializing PayPal Order...");
                return fetch("/create_order", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "Content-Type": "application/json",
                        "X-Requested-With": "XMLHttpRequest"
                    }
                })
                .then(res => {
                    hideLoadingOverlay();
                    if (res.status === 403) {
                        showToast("Login required to complete checkout.", "warning");
                        window.location.href = "/login";
                        throw new Error("Not logged in");
                    }
                    if (!res.ok) {
                        throw new Error("Order init network error");
                    }
                    return res.json();
                })
                .then(data => {
                    if (data.status === "not_logged_in" || data.redirect) {
                        showToast("Authentication required.", "warning");
                        window.location.href = data.redirect || "/login";
                        throw new Error("Not logged in");
                    }
                    if (!data.id) {
                        showToast("PayPal failed to initialize order token.", "danger");
                        throw new Error("Order creation failed");
                    }
                    return data.id;
                })
                .catch(err => {
                    hideLoadingOverlay();
                    console.error("Order Creation Error:", err);
                    showToast("Unable to start checkout. Check network status.", "danger");
                });
            },

            onApprove: function (data) {
                const shippingAddress = document.getElementById("shipping_address")?.value || "Demo Address";
                showLoadingOverlay("Capturing Payment...");
                
                return fetch("/capture_payment", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: JSON.stringify({
                        orderID: data.orderID,
                        shipping_address: shippingAddress
                    })
                })
                .then(res => {
                    hideLoadingOverlay();
                    if (res.status === 403) {
                        showToast("Login required to capture payment.", "warning");
                        window.location.href = "/login";
                        throw new Error("Session expired");
                    }
                    return res.json();
                })
                .then(details => {
                    if (details.status === "success") {
                        showToast("Payment Captured! Order Created.", "success");
                        setTimeout(() => {
                            window.location.href = "/order_success/" + details.order_id;
                        }, 1000);
                    } else if (details.status === "not_logged_in") {
                        showToast("Authentication required.", "warning");
                        window.location.href = "/login";
                    } else {
                        showToast("PayPal transaction declined/failed.", "danger");
                    }
                })
                .catch(err => {
                    hideLoadingOverlay();
                    console.error("Capture Error:", err);
                    showToast("Error recording purchase status.", "danger");
                });
            },

            onError: function (err) {
                hideLoadingOverlay();
                console.error("PayPal Flow Error:", err);
                showToast("PayPal SDK communication failure.", "danger");
            }
        }).render("#paypal-button-container");
    }

    // -------------------------
    // 7. Contact/Connect Form Handling
    // -------------------------
    const copyContactEmailBtn = document.getElementById("copyContactEmailBtn");
    const contactEmailText = document.getElementById("contactEmailText");
    if (copyContactEmailBtn && contactEmailText) {
        copyContactEmailBtn.addEventListener("click", function () {
            const email = contactEmailText.textContent.trim();
            navigator.clipboard.writeText(email).then(() => {
                const originalText = copyContactEmailBtn.textContent;
                copyContactEmailBtn.textContent = "Copied!";
                showToast("Email address copied to clipboard!", "success");
                setTimeout(() => {
                    copyContactEmailBtn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error("Failed to copy email: ", err);
                showToast("Failed to copy email. Please copy manually.", "danger");
            });
        });
    }

    const contactForm = document.getElementById("contactForm");
    if (contactForm) {
        contactForm.addEventListener("submit", function (e) {
            e.preventDefault();
            
            const nameInput = document.getElementById("contactName");
            const emailInput = document.getElementById("contactEmail");
            const subjectInput = document.getElementById("contactSubject");
            const messageInput = document.getElementById("contactMessage");

            let isValid = true;

            function validateField(input, condition) {
                if (condition) {
                    input.classList.remove("is-invalid");
                    input.classList.add("is-valid");
                } else {
                    input.classList.remove("is-valid");
                    input.classList.add("is-invalid");
                    isValid = false;
                }
            }

            validateField(nameInput, nameInput.value.trim().length > 0);

            const emailRegex = /^[\w\.-]+@[\w\.-]+\.\w+$/;
            validateField(emailInput, emailRegex.test(emailInput.value.trim()));

            validateField(subjectInput, subjectInput.value.trim().length > 0);

            validateField(messageInput, messageInput.value.trim().length >= 10);

            if (!isValid) {
                showToast("Please correct the errors in the contact form.", "warning");
                return;
            }

            const csrfToken = getCSRFToken();
            const submitBtn = contactForm.querySelector("button[type='submit']");
            const originalBtnText = submitBtn.innerHTML;

            submitBtn.disabled = true;
            submitBtn.innerHTML = 'Sending...';

            fetch("/submit_contact", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: JSON.stringify({
                    name: nameInput.value.trim(),
                    email: emailInput.value.trim(),
                    subject: subjectInput.value.trim(),
                    message: messageInput.value.trim()
                })
            })
            .then(res => res.json().then(data => ({ status: res.status, body: data })))
            .then(resData => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;

                if (resData.status === 200) {
                    showToast(resData.body.message, "success");
                    contactForm.reset();
                    [nameInput, emailInput, subjectInput, messageInput].forEach(el => {
                        el.classList.remove("is-valid", "is-invalid");
                    });
                } else {
                    showToast(resData.body.message || "An error occurred.", "danger");
                }
            })
            .catch(err => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
                console.error("Submission error:", err);
                showToast("Failed to send message. Please verify network connectivity.", "danger");
            });
        });
    }
});