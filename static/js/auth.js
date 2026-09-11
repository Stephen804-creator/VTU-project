document
    .getElementById("logout-button")
    .addEventListener(
        "click",
        async function() {

            try {

                await apiRequest(
                    "/auth/logout",
                    {
                        method: "POST"
                    }
                );

                // Only change the UI after the server
                // successfully logs the user out.
                showAuth();

                showMessage(
                    "auth-message",
                    "You have been logged out.",
                    "info"
                );

            } catch (error) {

                console.error(
                    "Logout error:",
                    error
                );

                // Keep the dashboard visible because
                // the server logout was not confirmed.
                showMessage(
                    "auth-message",
                    error.message ||
                    "Logout failed. Please try again.",
                    "error"
                );
            }
        }
    );
