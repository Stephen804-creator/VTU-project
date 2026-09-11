async function loadWallet() {

    try {

        const result =
            await apiRequest(
                "/wallet"
            );


        const wallet =
            result.data.wallet;


        document.getElementById(
            "wallet-balance"
        ).textContent =
            formatNairaFromKobo(
                wallet.balance_kobo
            );


    } catch (error) {

        showMessage(
            "data-message",
            error.message,
            "error"
        );
    }
}


/* ==========================================
   OPEN FUND WALLET MODAL
========================================== */

document
    .getElementById(
        "fund-wallet-button"
    )
    .addEventListener(
        "click",
        function() {

            showElement(
                "fund-wallet-modal"
            );

            // Clear previous input and messages
            document.getElementById(
                "fund-amount"
            ).value = "";

            hideElement(
                "wallet-message"
            );
        }
    );


/* ==========================================
   CLOSE MODAL
========================================== */

document
    .getElementById(
        "close-fund-modal"
    )
    .addEventListener(
        "click",
        function() {

            hideElement(
                "fund-wallet-modal"
            );

            hideElement(
                "wallet-message"
            );

            document.getElementById(
                "fund-amount"
            ).value = "";
        }
    );


/* ==========================================
   CREATE PAYMENT
========================================== */

document
    .getElementById(
        "create-payment-button"
    )
    .addEventListener(
        "click",
        createPayment
    );


async function createPayment() {

    const amountInput =
        document.getElementById(
            "fund-amount"
        );

    const amount = parseFloat(
        amountInput.value
    );

    if (!amount || amount <= 0) {

        showMessage(
            "wallet-message",
            "Enter a valid funding amount.",
            "error"
        );

        return;
    }

    const button =
        document.getElementById(
            "create-payment-button"
        );

    button.disabled = true;
    button.textContent = "Processing...";

    try {

        const result = await apiRequest(
            "/payments/create",
            {
                method: "POST",

                body: JSON.stringify({
                    amount: amount
                })
            }
        );

        const authorizationUrl =
            result.data
                .authorization_url;

        if (!authorizationUrl) {

            throw new Error(
                "Payment checkout URL was not returned."
            );
        }

        // Store payment reference for callback handling
        const paymentReference =
            result.data.payment.reference;

        // Store in sessionStorage so we can verify it after redirect
        sessionStorage.setItem(
            "subscribeMe_paymentReference",
            paymentReference
        );

        // Close modal before redirect
        hideElement(
            "fund-wallet-modal"
        );

        /*
         * Send the customer to Paystack Checkout.
         */
        window.location.href =
            authorizationUrl;

    } catch (error) {

        showMessage(
            "wallet-message",
            error.message,
            "error"
        );

        button.disabled = false;
        button.textContent = "Continue";
    }
}
