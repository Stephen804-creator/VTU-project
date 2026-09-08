const API_BASE = "/api/v1";


async function apiRequest(
    endpoint,
    options = {}
) {

    const config = {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    };


    const response = await fetch(
        `${API_BASE}${endpoint}`,
        config
    );


    let result;

    try {

        result = await response.json();

    } catch (error) {

        throw new Error(
            "Server returned an invalid response."
        );
    }


    if (!response.ok) {

        throw new Error(
            result.message ||
            "Request failed."
        );
    }


    return result;
}


function showMessage(
    elementId,
    message,
    type = "info"
) {

    const element = document.getElementById(
        elementId
    );

    if (!element) {
        return;
    }


    element.textContent = message;

    element.className =
        `message message-${type}`;
}


function hideElement(elementId) {

    const element = document.getElementById(
        elementId
    );

    if (element) {

        element.classList.add(
            "hidden"
        );
    }
}


function showElement(elementId) {

    const element = document.getElementById(
        elementId
    );

    if (element) {

        element.classList.remove(
            "hidden"
        );
    }
}


function formatNairaFromKobo(
    amountKobo
) {

    const amount =
        Number(amountKobo || 0) / 100;


    return new Intl.NumberFormat(
        "en-NG",
        {
            style: "currency",
            currency: "NGN"
        }
    ).format(amount);
}


function formatDate(
    dateString
) {

    if (!dateString) {
        return "-";
    }


    const date =
        new Date(
            dateString.replace(
                " ",
                "T"
            ) + "Z"
        );


    if (Number.isNaN(
        date.getTime()
    )) {

        return dateString;
    }


    return date.toLocaleString(
        "en-NG"
    );
}


async function loadCurrentUser() {

    try {

        const result =
            await apiRequest(
                "/auth/me"
            );

        return result.data.user;

    } catch (error) {

        return null;
    }
}


async function initializeApp() {

    const user =
        await loadCurrentUser();


    if (user) {

        showDashboard(
            user
        );

    } else {

        showAuth();
    }
}


function showDashboard(user) {

    hideElement(
        "auth-section"
    );

    showElement(
        "dashboard-section"
    );

    showElement(
        "user-area"
    );


    document.getElementById(
        "user-name"
    ).textContent =
        user.first_name
        || user.email;


    document.getElementById(
        "account-email"
    ).textContent =
        user.email;


    document.getElementById(
        "account-phone"
    ).textContent =
        user.phone
        || "No phone number";


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
}


function showAuth() {

    showElement(
        "auth-section"
    );

    hideElement(
        "dashboard-section"
    );

    hideElement(
        "user-area"
    );
}


document.addEventListener(
    "DOMContentLoaded",
    initializeApp
);
