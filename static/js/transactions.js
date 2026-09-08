async function loadTransactions() {

    const container =
        document.getElementById(
            "transactions-container"
        );


    if (!container) {
        return;
    }


    container.innerHTML =
        "<p>Loading transactions...</p>";


    try {

        const result =
            await apiRequest(
                "/transactions"
            );


        const walletTransactions =
            result.data.wallet_transactions
            || [];


        const orders =
            result.data.orders
            || [];


        container.innerHTML = "";


        if (
            !walletTransactions.length
            &&
            !orders.length
        ) {

            container.innerHTML =
                "<p>No transactions yet.</p>";

            return;
        }


        walletTransactions.forEach(
            transaction => {

                renderWalletTransaction(
                    transaction,
                    container
                );
            }
        );


        orders.forEach(
            order => {

                renderOrder(
                    order,
                    container
                );
            }
        );


    } catch (error) {

        container.innerHTML =
            `<p>${escapeHtml(
                error.message
            )}</p>`;
    }
}


function renderWalletTransaction(
    transaction,
    container
) {

    const item =
        document.createElement(
            "div"
        );


    item.className =
        "transaction-item";


    const left =
        document.createElement(
            "div"
        );


    const title =
        document.createElement(
            "div"
        );


    title.className =
        "transaction-title";


    title.textContent =
        transaction.description
        ||
        `Wallet ${transaction.type}`;


    const meta =
        document.createElement(
            "div"
        );


    meta.className =
        "transaction-meta";


    meta.textContent =
        `${transaction.reference} • ${
            formatDate(
                transaction.created_at
            )
        }`;


    const right =
        document.createElement(
            "div"
        );


    right.className =
        "transaction-amount";


    right.textContent =
        `${transaction.type === "CREDIT"
            ? "+"
            : "-"
        }${formatNairaFromKobo(
            transaction.amount_kobo
        )}`;


    if (
        transaction.type === "CREDIT"
    ) {

        right.classList.add(
            "transaction-credit"
        );

    } else {

        right.classList.add(
            "transaction-debit"
        );
    }


    left.appendChild(
        title
    );

    left.appendChild(
        meta
    );


    item.appendChild(
        left
    );

    item.appendChild(
        right
    );


    container.appendChild(
        item
    );
}


function renderOrder(
    order,
    container
) {

    const item =
        document.createElement(
            "div"
        );


    item.className =
        "transaction-item";


    const left =
        document.createElement(
            "div"
        );


    const title =
        document.createElement(
            "div"
        );


    title.className =
        "transaction-title";


    title.textContent =
        `Data Purchase - ${
            order.plan_name
            || "Data Plan"
        }`;


    const meta =
        document.createElement(
            "div"
        );


    meta.className =
        "transaction-meta";


    meta.textContent =
        `${order.reference} • ${
            order.network
        } • ${
            order.phone
        } • ${
            order.status
        }`;


    const right =
        document.createElement(
            "div"
        );


    right.className =
        "transaction-amount";


    right.textContent =
        formatNairaFromKobo(
            order.amount_kobo
        );


    left.appendChild(
        title
    );

    left.appendChild(
        meta
    );


    item.appendChild(
        left
    );

    item.appendChild(
        right
    );


    container.appendChild(
        item
    );
}


document
    .getElementById(
        "refresh-transactions-button"
    )
    .addEventListener(
        "click",
        loadTransactions
    );
