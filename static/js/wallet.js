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

    const amount =
        document.getElementById(
            "fund-amount"
        ).value;


    if (!amount) {

        showMessage(
            "wallet-message",
            "Enter an amount.",
            "error"
        );

        return;
    }


    try {

        const result =
            await apiRequest(
                "/payments/create",
                {
                    method: "POST",
                    body: JSON.stringify({
                        amount
                    })
                }
            );


        const payment =
            result.data.payment;


        showMessage(
            "wallet-message",
            result.message,
            "info"
        );


        document.getElementById(
            "payment-reference"
        ).textContent =
            payment.reference;


        showElement(
            "payment-info"
        );


    } catch (error) {

        showMessage(
            "wallet-message",
            error.message,
            "error"
        );
    }
}
