using DOAA.ObjectRepository;
using System.Collections.Generic;
using UiPath.CodedWorkflows;
using UiPath.CodedWorkflows.DescriptorIntegration;
using UiPath.UIAutomationNext.API.Models;

namespace DOAA
{
    public class VeggieAiFrontendE2E : CodedWorkflow
    {
        // Object Repository screen descriptors are used directly via Descriptors.VeggieAI.*

        // Auth elements
        private const string ModeSignInButton = "ModeSignInButton";
        private const string ModeSignUpButton = "ModeSignUpButton";
        private const string AuthTitleText = "AuthTitleText";
        private const string EmailInput = "EmailInput";
        private const string PasswordInput = "PasswordInput";
        private const string FullNameInput = "FullNameInput";
        private const string TermsCheckbox = "TermsCheckbox";
        private const string CaptchaPromptText = "CaptchaPromptText";
        private const string CaptchaAnswerInput = "CaptchaAnswerInput";
        private const string AuthSubmitButton = "AuthSubmitButton";
        private const string AuthErrorText = "AuthErrorText";
        private const string AuthSuccessText = "AuthSuccessText";
        private const string AuthWarningText = "AuthWarningText";
        private const string DevOtpText = "DevOtpText";
        private const string OtpInput = "OtpInput";
        private const string OtpVerifyButton = "OtpVerifyButton";
        private const string ForgotPasswordLink = "ForgotPasswordLink";
        private const string ForgotEmailInput = "ForgotEmailInput";
        private const string ForgotSubmitButton = "ForgotSubmitButton";
        private const string ForgotBackButton = "ForgotBackButton";
        private const string GetStartedButton = "GetStartedButton";

        // Predict + history elements
        private const string SampleCapsicumButton = "SampleCapsicumButton";
        private const string SampleCarrotButton = "SampleCarrotButton";
        private const string SampleTomatoButton = "SampleTomatoButton";
        private const string PredictButton = "PredictButton";
        private const string BatchCompleteText = "BatchCompleteText";
        private const string ResultListText = "ResultListText";
        private const string HistoryTabButton = "HistoryTabButton";
        private const string HistoryTotalText = "HistoryTotalText";
        private const string HistoryCountBadgeText = "HistoryCountBadgeText";

        [Workflow]
        public void Execute(
            string email = "",
            string password = "",
            string fullName = "RPA Test User",
            string captchaCode = "",
            string authPageUrl = "",
            bool captchaRequired = true,
            bool allowSignUpFallback = false,
            bool allowDevOtp = true,
            bool exerciseForgotPassword = false
        )
        {
            if (string.IsNullOrWhiteSpace(email))
            {
                throw new System.Exception("Input 'email' is required.");
            }

            if (string.IsNullOrWhiteSpace(password))
            {
                throw new System.Exception("Input 'password' is required.");
            }

            var targetAuthUrl = NormalizeAuthUrl(authPageUrl);
            if (string.IsNullOrWhiteSpace(targetAuthUrl))
            {
                targetAuthUrl = "http://127.0.0.1:5000/auth";
            }

            dynamic auth = OpenAuthWithRetry(targetAuthUrl);
            System.Threading.Thread.Sleep(800);
            auth = EnsureAuthPage(auth, targetAuthUrl);

            if (exerciseForgotPassword)
            {
                RequestPasswordReset(auth, email);
            }

            // Primary sign-in attempt
            SetSignInMode(auth);
            auth = Login(auth, email, password, captchaCode, captchaRequired, authPageUrl);

            // Optional fallback: if login fails, try sign-up then sign-in again.
            var authError = ReadTextOrEmpty(auth, AuthErrorText);
            if (!string.IsNullOrWhiteSpace(authError) && allowSignUpFallback)
            {
                SignUp(auth, fullName, email, password, captchaCode, captchaRequired);
                HandleOtpIfShown(auth, allowDevOtp);
                SetSignInMode(auth);
                auth = EnsureAuthPage(auth, targetAuthUrl);
                auth = Login(auth, email, password, captchaCode, captchaRequired, authPageUrl);
            }

            HandleOtpIfShown(auth, allowDevOtp);
            ThrowIfAuthErrorVisible(auth, "Authentication did not complete.");

            var predict = uiAutomation.Open(Descriptors.VeggieAI.PredictScreen);
            RunBatchPrediction(predict);
            ValidateHistory(predict);
        }

        private dynamic OpenAuthWithRetry(string targetAuthUrl)
        {
            System.Exception lastError = null;

            // Create/activate the expected tab before first attach attempt.
            TryLaunchUrl(targetAuthUrl);
            System.Threading.Thread.Sleep(1200);

            for (var attempt = 0; attempt < 4; attempt++)
            {
                try
                {
                    return uiAutomation.Open(Descriptors.VeggieAI.AuthScreen);
                }
                catch (System.Exception ex)
                {
                    lastError = ex;

                    // Re-open URL and retry attach.
                    TryLaunchUrl(targetAuthUrl);
                    System.Threading.Thread.Sleep(1200 + (attempt * 500));
                }
            }

            if (TryResetBrowserToAuth(targetAuthUrl))
            {
                System.Threading.Thread.Sleep(1500);
                try
                {
                    return uiAutomation.Open(Descriptors.VeggieAI.AuthScreen);
                }
                catch (System.Exception ex)
                {
                    lastError = ex;
                }
            }

            throw new System.Exception(
                "Could not attach to AuthScreen. Ensure Chrome has a VeggieAI tab at: " + targetAuthUrl +
                ". Last attach error: " + (lastError == null ? "unknown" : lastError.Message),
                lastError
            );
        }

        private void RequestPasswordReset(dynamic auth, string email)
        {
            if (!TryClick(auth, ForgotPasswordLink))
            {
                throw new System.Exception("ForgotPasswordLink mapping was not found.");
            }

            System.Threading.Thread.Sleep(300);
            if (!TryType(auth, ForgotEmailInput, email))
            {
                throw new System.Exception("ForgotEmailInput mapping was not found.");
            }

            if (!TryClick(auth, ForgotSubmitButton))
            {
                throw new System.Exception("ForgotSubmitButton mapping was not found.");
            }

            System.Threading.Thread.Sleep(1500);

            var success = ReadTextOrEmpty(auth, AuthSuccessText);
            var warning = ReadTextOrEmpty(auth, AuthWarningText);
            if (string.IsNullOrWhiteSpace(success) && string.IsNullOrWhiteSpace(warning))
            {
                throw new System.Exception("Forgot-password request did not return success/warning feedback.");
            }

            // Move back to sign-in state before continuing.
            TryClick(auth, ForgotBackButton);
            System.Threading.Thread.Sleep(300);
        }

        private void SetSignInMode(dynamic auth)
        {
            // Sign-in is typically the default mode. If the tab is temporarily unavailable,
            // continue and let Login fail only if required inputs truly cannot be reached.
            TryClickOptional(auth, ModeSignInButton, retries: 3, delayMs: 300);
            System.Threading.Thread.Sleep(250);
        }

        private void SetSignUpMode(dynamic auth)
        {
            if (!TryClickOptional(auth, ModeSignUpButton, retries: 3, delayMs: 300))
            {
                throw new System.Exception(
                    "Failed to switch to Sign Up mode. Re-indicate 'ModeSignUpButton' in Object Repository."
                );
            }
            System.Threading.Thread.Sleep(250);
        }

        private dynamic Login(
            dynamic auth,
            string email,
            string password,
            string captchaCode,
            bool captchaRequired,
            string authPageUrl
        )
        {
            if (!TryFillLoginCredentials(auth, email, password))
            {
                throw new System.Exception(
                    "Unable to set login credentials. Re-indicate 'EmailInput' and 'PasswordInput' " +
                    "under VeggieAI.AuthScreen, or verify the auth page structure has not changed."
                );
            }

            FillCaptchaIfVisible(auth, captchaCode, captchaRequired);

            if (!TryClick(auth, AuthSubmitButton))
            {
                throw new System.Exception("AuthSubmitButton mapping was not found.");
            }

            System.Threading.Thread.Sleep(1500);
            return auth;
        }

        private bool TryFillLoginCredentials(dynamic auth, string email, string password)
        {
            var emailDone = TryTypeOptional(auth, EmailInput, email, retries: 4, delayMs: 350);
            var passwordDone = TryTypeOptional(auth, PasswordInput, password, retries: 4, delayMs: 350);
            if (emailDone && passwordDone)
            {
                return true;
            }

            if (!emailDone)
            {
                emailDone = TrySetValueOptional(auth, EmailInput, email, retries: 3, delayMs: 300);
            }

            if (!passwordDone)
            {
                passwordDone = TrySetValueOptional(auth, PasswordInput, password, retries: 3, delayMs: 300);
            }

            if (emailDone && passwordDone)
            {
                return true;
            }

            if (!emailDone || !passwordDone)
            {
                var byModel = TryFillCredentialsByTargetModel(auth, email, password);
                if (byModel)
                {
                    return true;
                }
            }

            if (!emailDone || !passwordDone)
            {
                var raw = TryFillCredentialsByRawSelectors(auth, email, password);
                if (raw)
                {
                    return true;
                }
            }

            return TrySetCredentialsViaJs(auth, email, password);
        }

        private static bool TryFillCredentialsByTargetModel(dynamic auth, string email, string password)
        {
            var emailTarget = CreateWebTarget("<webctrl tag='input' id='input-email' />");
            var passwordTarget = CreateWebTarget("<webctrl tag='input' id='input-password' />");

            var emailDone = TryTypeTargetModel(auth, emailTarget, email);
            if (!emailDone)
            {
                emailDone = TrySetValueTargetModel(auth, emailTarget, email);
            }

            var passwordDone = TryTypeTargetModel(auth, passwordTarget, password);
            if (!passwordDone)
            {
                passwordDone = TrySetValueTargetModel(auth, passwordTarget, password);
            }

            return emailDone && passwordDone;
        }

        private static bool TryFillCredentialsByRawSelectors(dynamic auth, string email, string password)
        {
            var emailTargets = new string[]
            {
                "<webctrl tag='input' id='input-email' />",
                "<webctrl tag='input' type='email' />",
                "<webctrl tag='input' name='email' />",
                "<webctrl tag='input' aria-label='*email*' />",
                "<webctrl tag='input' placeholder='*email*' />"
            };

            var passwordTargets = new string[]
            {
                "<webctrl tag='input' id='input-password' />",
                "<webctrl tag='input' type='password' />",
                "<webctrl tag='input' name='password' />",
                "<webctrl tag='input' aria-label='*password*' />",
                "<webctrl tag='input' placeholder='*password*' />"
            };

            var emailDone = TryTypeToAnyTarget(auth, emailTargets, email);
            if (!emailDone)
            {
                emailDone = TrySetValueToAnyTarget(auth, emailTargets, email);
            }

            var passwordDone = TryTypeToAnyTarget(auth, passwordTargets, password);
            if (!passwordDone)
            {
                passwordDone = TrySetValueToAnyTarget(auth, passwordTargets, password);
            }

            return emailDone && passwordDone;
        }

        private dynamic EnsureAuthPage(dynamic auth, string authPageUrl)
        {
            var targetAuthUrl = NormalizeAuthUrl(authPageUrl);
            if (string.IsNullOrWhiteSpace(targetAuthUrl))
            {
                targetAuthUrl = "http://127.0.0.1:5000/auth";
            }

            var currentUrl = TryGetCurrentUrl(auth);
            if (UrlLooksLikeAuth(currentUrl))
            {
                return auth;
            }

            // Keep navigation predictable: one direct navigate attempt, then one external launch + reattach.
            if (NavigateTo(auth, targetAuthUrl))
            {
                return auth;
            }

            if (TryLaunchUrl(targetAuthUrl))
            {
                System.Threading.Thread.Sleep(1500);
                try
                {
                    auth = uiAutomation.Open(Descriptors.VeggieAI.AuthScreen);
                    System.Threading.Thread.Sleep(600);
                    return auth;
                }
                catch
                {
                    // continue and return current handle
                }
            }

            // Do not hard-fail here; let Login attempt field interaction and surface precise selector errors.
            return auth;
        }

        private static bool TryResetBrowserToAuth(string authUrl)
        {
            try
            {
                foreach (var process in System.Diagnostics.Process.GetProcessesByName("chrome"))
                {
                    try
                    {
                        process.Kill();
                        process.WaitForExit(1500);
                    }
                    catch
                    {
                        // continue killing remaining processes
                    }
                }
            }
            catch
            {
                // continue with launch attempt even if process enumeration fails
            }

            System.Threading.Thread.Sleep(700);
            return TryLaunchUrl(authUrl);
        }

        private static bool TryLaunchUrl(string url)
        {
            if (string.IsNullOrWhiteSpace(url))
            {
                return false;
            }

            try
            {
                var psi = new System.Diagnostics.ProcessStartInfo(url)
                {
                    UseShellExecute = true
                };
                System.Diagnostics.Process.Start(psi);
                return true;
            }
            catch
            {
                return false;
            }
        }

        private static bool IsAuthInteractionReady(dynamic auth)
        {
            // Inputs may be blank, so GetText-based checks are unreliable.
            return TryClickOptional(auth, EmailInput, retries: 1, delayMs: 0)
                || TryClickOptional(auth, PasswordInput, retries: 1, delayMs: 0)
                || TryClickOptional(auth, AuthSubmitButton, retries: 1, delayMs: 0);
        }

        private static string TryGetCurrentUrl(dynamic auth)
        {
            try
            {
                var value = auth.GetUrl(new GetUrlOptions());
                return value == null ? string.Empty : value.ToString();
            }
            catch
            {
                return string.Empty;
            }
        }

        private static bool UrlLooksLikeAuth(string url)
        {
            if (string.IsNullOrWhiteSpace(url))
            {
                return false;
            }

            if (!System.Uri.TryCreate(url, System.UriKind.Absolute, out var parsed))
            {
                return false;
            }

            return parsed.AbsolutePath.TrimEnd('/').EndsWith("/auth", System.StringComparison.OrdinalIgnoreCase);
        }

        private static string BuildAuthUrl(string currentUrl)
        {
            if (!System.Uri.TryCreate(currentUrl, System.UriKind.Absolute, out var parsed))
            {
                return string.Empty;
            }

            var builder = new System.UriBuilder(parsed)
            {
                Path = "/auth",
                Query = string.Empty,
                Fragment = string.Empty
            };
            return builder.Uri.ToString();
        }

        private static string BuildSiblingAuthUrl(string currentUrl)
        {
            if (!System.Uri.TryCreate(currentUrl, System.UriKind.Absolute, out var parsed))
            {
                return string.Empty;
            }

            var trimmed = parsed.AbsolutePath.TrimEnd('/');
            if (string.IsNullOrWhiteSpace(trimmed))
            {
                return string.Empty;
            }

            var idx = trimmed.LastIndexOf('/');
            var prefix = idx > 0 ? trimmed.Substring(0, idx) : string.Empty;
            var siblingPath = string.Concat(prefix, "/auth");

            var builder = new System.UriBuilder(parsed)
            {
                Path = siblingPath,
                Query = string.Empty,
                Fragment = string.Empty
            };
            return builder.Uri.ToString();
        }

        private static string NormalizeAuthUrl(string authPageUrl)
        {
            if (string.IsNullOrWhiteSpace(authPageUrl))
            {
                return string.Empty;
            }

            var trimmed = authPageUrl.Trim();
            if (!trimmed.StartsWith("http://", System.StringComparison.OrdinalIgnoreCase)
                && !trimmed.StartsWith("https://", System.StringComparison.OrdinalIgnoreCase))
            {
                trimmed = "http://" + trimmed;
            }

            if (!System.Uri.TryCreate(trimmed, System.UriKind.Absolute, out var parsed))
            {
                return string.Empty;
            }

            var path = parsed.AbsolutePath.TrimEnd('/');
            if (!path.EndsWith("/auth", System.StringComparison.OrdinalIgnoreCase))
            {
                path = path + "/auth";
            }

            var builder = new System.UriBuilder(parsed)
            {
                Path = path,
                Query = string.Empty,
                Fragment = string.Empty
            };
            return builder.Uri.ToString();
        }

        private static void AddCandidate(List<string> candidates, string url)
        {
            if (string.IsNullOrWhiteSpace(url))
            {
                return;
            }

            if (!candidates.Contains(url))
            {
                candidates.Add(url);
            }
        }

        private static bool NavigateTo(dynamic auth, string url)
        {
            for (var attempt = 0; attempt < 3; attempt++)
            {
                try
                {
                    auth.GoToUrl(url);
                    System.Threading.Thread.Sleep(1200);
                    return true;
                }
                catch
                {
                    if (attempt < 2)
                    {
                        System.Threading.Thread.Sleep(500);
                    }
                }
            }

            return false;
        }

        private void SignUp(
            dynamic auth,
            string fullName,
            string email,
            string password,
            string captchaCode,
            bool captchaRequired
        )
        {
            SetSignUpMode(auth);

            if (!TryTypeOptional(auth, FullNameInput, fullName, retries: 4, delayMs: 350))
            {
                throw new System.Exception("FullNameInput mapping was not found.");
            }

            if (!TryTypeOptional(auth, EmailInput, email, retries: 4, delayMs: 350))
            {
                throw new System.Exception("EmailInput mapping was not found.");
            }

            if (!TryTypeOptional(auth, PasswordInput, password, retries: 4, delayMs: 350))
            {
                throw new System.Exception("PasswordInput mapping was not found.");
            }

            if (!TryClick(auth, TermsCheckbox))
            {
                throw new System.Exception("TermsCheckbox mapping was not found.");
            }

            FillCaptchaIfVisible(auth, captchaCode, captchaRequired);

            if (!TryClick(auth, AuthSubmitButton))
            {
                throw new System.Exception("AuthSubmitButton mapping was not found.");
            }

            System.Threading.Thread.Sleep(1500);
            ThrowIfAuthErrorVisible(auth, "Sign-up request failed.");
        }

        private void FillCaptchaIfVisible(dynamic auth, string captchaCode, bool captchaRequired)
        {
            var captchaVisible =
                !string.IsNullOrWhiteSpace(ReadTextOrEmpty(auth, CaptchaPromptText))
                || ElementProbablyPresent(auth, CaptchaAnswerInput);

            if (!captchaVisible)
            {
                return;
            }

            if (string.IsNullOrWhiteSpace(captchaCode))
            {
                if (captchaRequired)
                {
                    throw new System.Exception(
                        "Captcha is visible. Provide workflow input 'captchaCode'. " +
                        "For unattended runs, enable CAPTCHA_DEV_MODE and fetch captcha_text from API."
                    );
                }
                return;
            }

            if (!TryTypeOptional(auth, CaptchaAnswerInput, captchaCode.Trim(), retries: 3, delayMs: 300))
            {
                throw new System.Exception("CaptchaAnswerInput mapping was not found.");
            }
        }

        private void HandleOtpIfShown(dynamic auth, bool allowDevOtp)
        {
            var title = ReadTextOrEmpty(auth, AuthTitleText);
            var otpVisible =
                title.IndexOf("verify otp", System.StringComparison.OrdinalIgnoreCase) >= 0
                || ElementProbablyPresent(auth, OtpInput);

            if (!otpVisible)
            {
                return;
            }

            if (!allowDevOtp)
            {
                throw new System.Exception(
                    "OTP verification screen detected. Set allowDevOtp=true and OTP_DEV_MODE=true for unattended run."
                );
            }

            var devOtpLabel = ReadTextOrEmpty(auth, DevOtpText);
            var otp = ExtractOtp(devOtpLabel);
            if (string.IsNullOrWhiteSpace(otp))
            {
                throw new System.Exception(
                    "OTP verification screen is visible but no development OTP was found. " +
                    "Check DevOtpText mapping and OTP_DEV_MODE setting."
                );
            }

            if (!TryTypeOptional(auth, OtpInput, otp, retries: 3, delayMs: 300))
            {
                throw new System.Exception("OtpInput mapping was not found.");
            }

            if (!TryClick(auth, OtpVerifyButton))
            {
                throw new System.Exception("OtpVerifyButton mapping was not found.");
            }

            System.Threading.Thread.Sleep(1200);
        }

        private void ThrowIfAuthErrorVisible(dynamic auth, string defaultMessage)
        {
            var message = ReadTextOrEmpty(auth, AuthErrorText);
            if (!string.IsNullOrWhiteSpace(message))
            {
                throw new System.Exception($"Auth error: {message}");
            }

            // Defensive fallback for cases where error is shown as warning.
            var warning = ReadTextOrEmpty(auth, AuthWarningText);
            if (
                !string.IsNullOrWhiteSpace(warning)
                && warning.IndexOf("error", System.StringComparison.OrdinalIgnoreCase) >= 0
            )
            {
                throw new System.Exception($"Auth warning indicates failure: {warning}");
            }

            // If sign-in page still says welcome back after flow, this may indicate a failed auth.
            var title = ReadTextOrEmpty(auth, AuthTitleText);
            if (
                title.IndexOf("welcome back", System.StringComparison.OrdinalIgnoreCase) >= 0
                && string.IsNullOrWhiteSpace(ReadTextOrEmpty(auth, AuthSuccessText))
            )
            {
                // Don't fail hard unless there is also no OTP state, because redirect may already be in progress.
                if (!ElementProbablyPresent(auth, OtpInput))
                {
                    throw new System.Exception(defaultMessage);
                }
            }
        }

        private void RunBatchPrediction(dynamic predict)
        {
            if (!TryClick(predict, SampleCapsicumButton))
            {
                throw new System.Exception("SampleCapsicumButton mapping was not found.");
            }
            System.Threading.Thread.Sleep(200);

            if (!TryClick(predict, SampleCarrotButton))
            {
                throw new System.Exception("SampleCarrotButton mapping was not found.");
            }
            System.Threading.Thread.Sleep(200);

            if (!TryClick(predict, SampleTomatoButton))
            {
                throw new System.Exception("SampleTomatoButton mapping was not found.");
            }
            System.Threading.Thread.Sleep(200);

            if (!TryClick(predict, PredictButton))
            {
                throw new System.Exception("PredictButton mapping was not found.");
            }

            WaitUntil(
                condition: () =>
                    !string.IsNullOrWhiteSpace(ReadTextOrEmpty(predict, BatchCompleteText))
                    || !string.IsNullOrWhiteSpace(ReadTextOrEmpty(predict, ResultListText))
                    || TextContainsNumber(ReadTextOrEmpty(predict, HistoryCountBadgeText)),
                timeoutMs: 35000,
                pollMs: 500,
                timeoutMessage: "Batch prediction did not finish in time."
            );
        }

        private void ValidateHistory(dynamic predict)
        {
            if (!TryClick(predict, HistoryTabButton))
            {
                throw new System.Exception("HistoryTabButton mapping was not found.");
            }
            System.Threading.Thread.Sleep(900);

            WaitUntil(
                condition: () =>
                    !string.IsNullOrWhiteSpace(ReadTextOrEmpty(predict, HistoryTotalText)),
                timeoutMs: 12000,
                pollMs: 400,
                timeoutMessage: "History total text not found."
            );

            var total = ReadTextOrEmpty(predict, HistoryTotalText);
            if (!total.Contains("prediction", System.StringComparison.OrdinalIgnoreCase))
            {
                throw new System.Exception($"History total text is unexpected: '{total}'");
            }
            if (!TextContainsNumber(total))
            {
                throw new System.Exception($"History total does not contain numeric count: '{total}'");
            }
        }

        private static bool TryClick(dynamic screen, string elementName)
        {
            var descriptor = ResolveElementDescriptor(elementName);

            System.Exception descriptorError = null;
            try
            {
                if (descriptor != null)
                {
                    screen.Click(descriptor, new ClickOptions());
                    return true;
                }
            }
            catch (System.Exception ex)
            {
                descriptorError = ex;
            }

            try
            {
                screen.Click(elementName);
                return true;
            }
            catch (System.Exception ex)
            {
                if (descriptorError != null)
                {
                    throw new System.Exception(
                        $"Failed to click '{elementName}'. Descriptor error: {descriptorError.Message}. Name fallback error: {ex.Message}",
                        ex
                    );
                }
                throw new System.Exception($"Failed to click '{elementName}': {ex.Message}", ex);
            }
        }

        private static bool TryClickOptional(dynamic screen, string elementName, int retries, int delayMs)
        {
            for (var i = 0; i < retries; i++)
            {
                try
                {
                    if (TryClick(screen, elementName))
                    {
                        return true;
                    }
                }
                catch
                {
                    // Optional click path: swallow transient targeting failures.
                }

                if (i < retries - 1)
                {
                    System.Threading.Thread.Sleep(delayMs);
                }
            }

            return false;
        }

        private static bool TryType(dynamic screen, string elementName, string value)
        {
            var descriptor = ResolveElementDescriptor(elementName);

            System.Exception descriptorError = null;
            try
            {
                if (descriptor != null)
                {
                    screen.TypeInto(descriptor, value);
                    return true;
                }
            }
            catch (System.Exception ex)
            {
                descriptorError = ex;
            }

            try
            {
                screen.TypeInto(elementName, value);
                return true;
            }
            catch (System.Exception ex)
            {
                if (descriptorError != null)
                {
                    throw new System.Exception(
                        $"Failed to type into '{elementName}'. Descriptor error: {descriptorError.Message}. Name fallback error: {ex.Message}",
                        ex
                    );
                }
                throw new System.Exception($"Failed to type into '{elementName}': {ex.Message}", ex);
            }
        }

        private static bool TryTypeOptional(dynamic screen, string elementName, string value, int retries, int delayMs)
        {
            for (var i = 0; i < retries; i++)
            {
                try
                {
                    // Focus the target first, then type.
                    TryClickOptional(screen, elementName, retries: 1, delayMs: 0);
                    if (TryType(screen, elementName, value))
                    {
                        return true;
                    }
                }
                catch
                {
                    // retry
                }

                if (i < retries - 1)
                {
                    System.Threading.Thread.Sleep(delayMs);
                }
            }

            return false;
        }

        private static bool TrySetValue(dynamic screen, string elementName, string value)
        {
            var descriptor = ResolveElementDescriptor(elementName);

            System.Exception descriptorError = null;
            try
            {
                if (descriptor != null)
                {
                    screen.SetValue(descriptor, value);
                    return true;
                }
            }
            catch (System.Exception ex)
            {
                descriptorError = ex;
            }

            try
            {
                screen.SetValue(elementName, value);
                return true;
            }
            catch (System.Exception ex)
            {
                if (descriptorError != null)
                {
                    throw new System.Exception(
                        $"Failed to set value for '{elementName}'. Descriptor error: {descriptorError.Message}. Name fallback error: {ex.Message}",
                        ex
                    );
                }
                throw new System.Exception($"Failed to set value for '{elementName}': {ex.Message}", ex);
            }
        }

        private static bool TrySetValueOptional(dynamic screen, string elementName, string value, int retries, int delayMs)
        {
            for (var i = 0; i < retries; i++)
            {
                try
                {
                    TryClickOptional(screen, elementName, retries: 1, delayMs: 0);
                    if (TrySetValue(screen, elementName, value))
                    {
                        return true;
                    }
                }
                catch
                {
                    // retry
                }

                if (i < retries - 1)
                {
                    System.Threading.Thread.Sleep(delayMs);
                }
            }

            return false;
        }

        private static bool TrySetCredentialsViaJs(dynamic auth, string email, string password)
        {
            var script = @"
var raw = inputParameter || '';
var parts = raw.split('|');
function b64Decode(v) {
    try {
        return decodeURIComponent(escape(window.atob(v || '')));
    } catch (e) {
        try {
            return window.atob(v || '');
        } catch (x) {
            return '';
        }
    }
}
function pickInput(kind) {
    var inputs = document.getElementsByTagName('input');
    for (var i = 0; i < inputs.length; i++) {
        var el = inputs[i];
        var type = (el.getAttribute('type') || '').toLowerCase();
        var name = (el.getAttribute('name') || '').toLowerCase();
        var id = (el.getAttribute('id') || '').toLowerCase();
        var placeholder = (el.getAttribute('placeholder') || '').toLowerCase();
        var autocomplete = (el.getAttribute('autocomplete') || '').toLowerCase();
        if (kind === 'email') {
            if (type === 'email' || name.indexOf('email') >= 0 || id.indexOf('email') >= 0 || placeholder.indexOf('email') >= 0 || autocomplete.indexOf('email') >= 0) {
                return el;
            }
        }
        if (kind === 'password') {
            if (type === 'password' || name.indexOf('password') >= 0 || id.indexOf('password') >= 0 || placeholder.indexOf('password') >= 0 || autocomplete.indexOf('password') >= 0) {
                return el;
            }
        }
    }
    return null;
}
function setValue(el, value) {
    if (!el) return false;
    el.focus();
    el.value = '';
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.value = value || '';
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
}
var emailValue = b64Decode(parts.length > 0 ? parts[0] : '');
var passwordValue = b64Decode(parts.length > 1 ? parts[1] : '');
var emailEl = document.getElementById('input-email') || pickInput('email');
var passwordEl = document.getElementById('input-password') || pickInput('password');
var emailOk = setValue(emailEl, emailValue);
var passwordOk = setValue(passwordEl, passwordValue);
return JSON.stringify({ email: emailOk, password: passwordOk, href: window.location.href });";

            var encodedEmail = System.Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(email ?? string.Empty));
            var encodedPassword = System.Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(password ?? string.Empty));
            var inputParameter = encodedEmail + "|" + encodedPassword;

            var rawTargets = new string[]
            {
                "<webctrl tag='html' />",
                "<webctrl tag='body' />"
            };

            for (var i = 0; i < rawTargets.Length; i++)
            {
                try
                {
                    var rawResult = auth.InjectJsScript(rawTargets[i], script, inputParameter);
                    var rawOutput = rawResult == null ? string.Empty : rawResult.ToString();
                    if (
                        rawOutput.IndexOf("\"email\":true", System.StringComparison.OrdinalIgnoreCase) >= 0
                        && rawOutput.IndexOf("\"password\":true", System.StringComparison.OrdinalIgnoreCase) >= 0
                    )
                    {
                        return true;
                    }
                }
                catch
                {
                    // Continue with descriptor/name anchors.
                }
            }

            var anchors = new string[]
            {
                AuthTitleText,
                AuthSubmitButton,
                PasswordInput,
                EmailInput,
                ModeSignInButton
            };

            for (var i = 0; i < anchors.Length; i++)
            {
                var anchor = anchors[i];
                var descriptor = ResolveElementDescriptor(anchor);
                try
                {
                    object result;
                    if (descriptor != null)
                    {
                        result = auth.InjectJsScript(descriptor, script, inputParameter);
                    }
                    else
                    {
                        result = auth.InjectJsScript(anchor, script, inputParameter);
                    }

                    var output = result == null ? string.Empty : result.ToString();
                    if (
                        output.IndexOf("\"email\":true", System.StringComparison.OrdinalIgnoreCase) >= 0
                        && output.IndexOf("\"password\":true", System.StringComparison.OrdinalIgnoreCase) >= 0
                    )
                    {
                        return true;
                    }
                }
                catch
                {
                    // Try next anchor.
                }
            }

            return false;
        }

        private static bool TryTypeToAnyTarget(dynamic screen, string[] targets, string value)
        {
            for (var i = 0; i < targets.Length; i++)
            {
                var target = targets[i];
                try
                {
                    screen.TypeInto(target, value);
                    return true;
                }
                catch
                {
                    // Try next target.
                }
            }

            return false;
        }

        private static bool TryTypeTargetModel(dynamic auth, TargetAnchorableModel target, string value)
        {
            try
            {
                auth.TypeInto(target, value);
                return true;
            }
            catch
            {
                return false;
            }
        }

        private static bool TrySetValueToAnyTarget(dynamic screen, string[] targets, string value)
        {
            for (var i = 0; i < targets.Length; i++)
            {
                var target = targets[i];
                try
                {
                    screen.SetValue(target, value);
                    return true;
                }
                catch
                {
                    // Try next target.
                }
            }

            return false;
        }

        private static bool TrySetValueTargetModel(dynamic auth, TargetAnchorableModel target, string value)
        {
            try
            {
                auth.SetValue(target, value);
                return true;
            }
            catch
            {
                return false;
            }
        }

        private static TargetAnchorableModel CreateWebTarget(string partialSelector)
        {
            return new TargetAnchorableModel
            {
                ScopeSelector = "<wnd app='chrome.exe' cls='Chrome_WidgetWin_1' title='VeggieAI | * - Google Chrome' />",
                PartialSelector = partialSelector
            };
        }

        private static string ReadTextOrEmpty(dynamic screen, string elementName)
        {
            try
            {
                var descriptor = ResolveElementDescriptor(elementName);
                var value = descriptor != null ? screen.GetText(descriptor) : screen.GetText(elementName);
                return value == null ? string.Empty : value.ToString();
            }
            catch
            {
                return string.Empty;
            }
        }

        private static bool ElementProbablyPresent(dynamic screen, string elementName)
        {
            var value = ReadTextOrEmpty(screen, elementName);
            return !string.IsNullOrWhiteSpace(value);
        }

        private static IElementDescriptor ResolveElementDescriptor(string elementName)
        {
            var auth = Descriptors.VeggieAI.AuthScreen;
            var predict = Descriptors.VeggieAI.PredictScreen;

            switch (elementName)
            {
                case ModeSignInButton: return auth.ModeSignInButton;
                case ModeSignUpButton: return auth.ModeSignUpButton;
                case AuthTitleText: return auth.AuthTitleText;
                case EmailInput: return auth.EmailInput;
                case PasswordInput: return auth.PasswordInput;
                case FullNameInput: return auth.FullNameInput;
                case TermsCheckbox: return auth.TermsCheckbox;
                case CaptchaPromptText: return auth.CaptchaPromptText;
                case CaptchaAnswerInput: return auth.CaptchaAnswerInput;
                case AuthSubmitButton: return auth.AuthSubmitButton;
                case AuthErrorText: return auth.AuthErrorText;
                case AuthSuccessText: return auth.AuthSuccessText;
                case AuthWarningText: return auth.AuthWarningText;
                case DevOtpText: return auth.DevOtpText;
                case OtpInput: return auth.OtpInput;
                case OtpVerifyButton: return auth.OtpVerifyButton;
                case ForgotPasswordLink: return auth.ForgotPasswordLink;
                case ForgotEmailInput: return auth.ForgotEmailInput;
                case ForgotSubmitButton: return auth.ForgotSubmitButton;
                case ForgotBackButton: return auth.ForgotBackButton;
                case SampleCapsicumButton: return predict.SampleCapsicumButton;
                case SampleCarrotButton: return predict.SampleCarrotButton;
                case SampleTomatoButton: return predict.SampleTomatoButton;
                case PredictButton: return predict.PredictButton;
                case BatchCompleteText: return predict.BatchCompleteText;
                case ResultListText: return predict.ResultListText;
                case HistoryTabButton: return predict.HistoryTabButton;
                case HistoryTotalText: return predict.HistoryTotalText;
                case HistoryCountBadgeText: return predict.HistoryCountBadgeText;
                default: return null;
            }
        }

        private static string ExtractOtp(string label)
        {
            if (string.IsNullOrWhiteSpace(label))
            {
                return string.Empty;
            }

            var match = System.Text.RegularExpressions.Regex.Match(label, @"(\d{4,12})");
            return match.Success ? match.Groups[1].Value : string.Empty;
        }

        private static bool TextContainsNumber(string value)
        {
            return System.Text.RegularExpressions.Regex.IsMatch(value ?? string.Empty, @"\d+");
        }

        private static void WaitUntil(
            System.Func<bool> condition,
            int timeoutMs,
            int pollMs,
            string timeoutMessage
        )
        {
            var started = System.Environment.TickCount;
            while (System.Environment.TickCount - started < timeoutMs)
            {
                if (condition())
                {
                    return;
                }
                System.Threading.Thread.Sleep(pollMs);
            }

            throw new System.TimeoutException(timeoutMessage);
        }
    }
}
