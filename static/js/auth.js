document
    .getElementById("login-form")
    .addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            const email =
                document.getElementById(
                    "login-email"
                ).value.trim();


            const password =
                document.getElementById(
                    "login-password"
                ).value;


            try {

                const result =
                    await apiRequest(
                        "/auth/login",
                        {
                            method: "POST",
                            body: JSON.stringify({
                                email,
                                password
                            })
                        }
                    );


                showMessage(
                    "auth-message",
                    result.message ||
                    "Login successful.",
                    "success"
                );


                showDashboard(
                    result.data.user
                );


                document
                    .getElementById(
                        "login-form"
                    )
                    .reset();


            } catch (error) {

                showMessage(
                    "auth-message",
                    error.message,
                    "error"
                );
            }
        }
    );


document
    .getElementById("register-form")
    .addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            const firstName =
                document.getElementById(
                    "register-first-name"
                ).value.trim();


            const lastName =
                document.getElementById(
                    "register-last-name"
                ).value.trim();


            const email =
                document.getElementById(
                    "register-email"
                ).value.trim();


            const phone =
                document.getElementById(
                    "register-phone"
                ).value.trim();


            const password =
                document.getElementById(
                    "register-password"
                ).value;


            try {

                const result =
                    await apiRequest(
                        "/auth/register",
                        {
                            method: "POST",
                            body: JSON.stringify({
                                first_name:
                                    firstName,
                                last_name:
                                    lastName,
                                email,
                                phone,
                                password
                            })
                        }
                    );


                showMessage(
                    "auth-message",
                    result.message ||
                    "Account created.",
                    "success"
                );


                showDashboard(
                    result.data.user
                );


                document
                    .getElementById(
                        "register-form"
                    )
                    .reset();


            } catch (error) {

                showMessage(
                    "auth-message",
                    error.message,
                    "error"
                );
            }
        }
    );


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

            } catch (error) {

                console.error(
                    "Logout error:",
                    error
                );

            } finally {

                showAuth();

                showMessage(
                    "auth-message",
                    "You have been logged out.",
                    "info"
                );
            }
        }
    );
