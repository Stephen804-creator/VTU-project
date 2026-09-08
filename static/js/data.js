let selectedPlan = null;


document
    .getElementById("load-plans-button")
    .addEventListener(
        "click",
        loadPlans
    );


async function loadPlans() {

    const network =
        document.getElementById(
            "network-select"
        ).value;


    const planType =
        document.getElementById(
            "plan-type-select"
        ).value;


    if (!network) {

        showMessage(
            "data-message",
            "Please select a network.",
            "error"
        );

        return;
    }


    if (!planType) {

        showMessage(
            "data-message",
            "Please select a plan type.",
            "error"
        );

        return;
    }


    const container =
        document.getElementById(
            "plans-container"
        );


    container.innerHTML = "";


    showElement(
        "plans-loading"
    );


    try {

        const result =
            await apiRequest(
                `/data/plans?network=${encodeURIComponent(
                    network
                )}&plan_type=${encodeURIComponent(
                    planType
                )}`
            );


        hideElement(
            "plans-loading"
        );


        const plans =
            result.data.plans;


        if (!plans.length) {

            container.innerHTML =
                "<p>No plans available for this selection.</p>";

            return;
        }


        plans.forEach(
            renderPlan
        );


    } catch (error) {

        hideElement(
            "plans-loading"
        );


        showMessage(
            "data-message",
            error.message,
            "error"
        );
    }
}


function renderPlan(plan) {

    const container =
        document.getElementById(
            "plans-container"
        );


    const card =
        document.createElement(
            "div"
        );


    card.className =
        "plan-card";


    const name =
        document.createElement(
            "h3"
        );


    name.textContent =
        plan.name;


    const dataAmount =
        document.createElement(
            "p"
        );


    dataAmount.className =
        "plan-meta";


    dataAmount.textContent =
        `Data: ${plan.data_amount || "-"}`;


    const validity =
        document.createElement(
            "p"
        );


    validity.className =
        "plan-meta";


    validity.textContent =
        `Validity: ${plan.validity || "-"}`;


    const price =
        document.createElement(
            "div"
        );


    price.className =
        "plan-price";


    price.textContent =
        formatNairaFromKobo(
            plan.price_kobo
        );


    const button =
        document.createElement(
            "button"
        );


    button.className =
        "button button-primary";


    button.textContent =
        "Select Plan";


    button.addEventListener(
        "click",
        function() {

            selectPlan(
                plan
            );
        }
    );


    card.appendChild(
        name
    );

    card.appendChild(
        dataAmount
    );

    card.appendChild(
        validity
    );

    card.appendChild(
        price
    );

    card.appendChild(
        button
    );


    container.appendChild(
        card
    );
}


function selectPlan(plan) {

    selectedPlan = plan;


    document.getElementById(
        "selected-plan-name"
    ).textContent =
        plan.name;


    document.getElementById(
        "selected-plan-price"
    ).textContent =
        formatNairaFromKobo(
            plan.price_kobo
        );


    showElement(
        "purchase-area"
    );


    document
        .getElementById(
            "purchase-area"
        )
        .scrollIntoView({
            behavior: "smooth"
        });
}


document
    .getElementById("purchase-button")
    .addEventListener(
        "click",
        preparePurchase
    );


function preparePurchase() {

    if (!selectedPlan) {

        showMessage(
            "data-message",
            "Please select a plan first.",
            "error"
        );

        return;
    }


    const phone =
        document.getElementById(
            "purchase-phone"
        ).value.trim();


    if (!phone) {

        showMessage(
            "data-message",
            "Enter the recipient phone number.",
            "error"
        );

        return;
    }


    document.getElementById(
        "order-summary"
    ).innerHTML = `
        <p>
            <strong>Plan:</strong>
            ${escapeHtml(selectedPlan.name)}
        </p>

        <p>
            <strong>Network:</strong>
            ${escapeHtml(selectedPlan.network)}
        </p>

        <p>
            <strong>Recipient:</strong>
            ${escapeHtml(phone)}
        </p>

        <p>
            <strong>Amount:</strong>
            ${formatNairaFromKobo(
                selectedPlan.price_kobo
            )}
        </p>
    `;


    showElement(
        "order-modal"
    );
}


document
    .getElementById("close-order-modal")
    .addEventListener(
        "click",
        function() {

            hideElement(
                "order-modal"
            );
        }
    );


document
    .getElementById("confirm-order-button")
    .addEventListener(
        "click",
        confirmPurchase
    );


async function confirmPurchase() {

    if (!selectedPlan) {
        return;
    }


    const phone =
        document.getElementById(
            "purchase-phone"
        ).value.trim();


    const button =
        document.getElementById(
            "confirm-order-button"
        );


    button.disabled = true;

    button.textContent =
        "Processing...";


    try {

        const result =
            await apiRequest(
                "/orders",
                {
                    method: "POST",
                    body: JSON.stringify({
                        plan_id:
                            selectedPlan.id,
                        phone
                    })
                }
            );


        hideElement(
            "order-modal"
        );


        showMessage(
            "data-message",
            result.message ||
            "Order processed.",
            "success"
        );


        document.getElementById(
            "purchase-phone"
        ).value = "";


        selectedPlan = null;


        hideElement(
            "purchase-area"
        );


        if (
            typeof loadWallet === "function"
        ) {

            loadWallet();
        }


        if (
            typeof loadTransactions === "function"
        ) {

            loadTransactions();
        }


    } catch (error) {

        showMessage(
            "data-message",
            error.message,
            "error"
        );

    } finally {

        button.disabled = false;

        button.textContent =
            "Confirm Purchase";
    }
}


function escapeHtml(value) {

    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        value ?? "";


    return div.innerHTML;
}
