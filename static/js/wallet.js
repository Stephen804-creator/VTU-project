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
            "fundAmount"
        );

    const amount = parseFloat(
        amountInput.value
    );

    if (!amount || amount <= 0) {

        showMessage(
            "Enter a valid funding amount.",
            "error"
        );

        return;
    }

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

        closeFundWalletModal();

        /*
         * Send the customer to Paystack Checkout.
         */
        window.location.href =
            authorizationUrl;

    } catch (error) {

        showMessage(
            error.message,
            "error"
        );
    }
}
