# Authenticated capture

`--login` supports websites that establish a cookie session through an ordinary HTML username/password form. It is optional; public captures keep their existing behavior.

## Capture a protected page

```sh
npm run crawl -- --url https://your-authorized-site.example/private/ --authorized --output captures/private --login --login-check '#signed-in'
```

The tool follows the target to its login form, then prompts for the username and password with both inputs hidden. Choose a CSS selector that identifies a visible signed-in element on every captured HTML page, such as the account navigation. A missing or hidden marker, or a returned password form, stops capture instead of validating the login page as the intended content.

`--login` takes no argument. Do not put `username:password` after it. Credentials are not read from environment variables, configuration files, command arguments, or redirected standard input. The prompt refuses an input fallback that would echo them. `--authorized` remains required and records permission to reproduce the target.

Select a different login page or ambiguous form fields explicitly:

```sh
npm run crawl -- --url https://your-authorized-site.example/private/ --authorized --output captures/private --login --login-url https://your-authorized-site.example/sign-in --login-check '#account-navigation' --login-form '#login-form' --login-user-field email --login-password-field password
```

The field options name HTML input `name` attributes. The form and check options use CSS selectors. Without overrides, the tool requires one form containing one password field and one username field. It prefers `autocomplete="username"`, then an email/text input. Hidden form inputs, including ordinary CSRF fields, accompany the credential POST.

## Where login data goes

The initial form is fetched with the native HTTP client. The username and password are sent once in a URL-encoded POST to a form action on the target's exact scheme, hostname, and port. HTTPS is required, except for loopback HTTP test sites. Cross-origin actions and redirects are refused. A 307/308 redirect that would resend the credential POST is also refused.

Login requests run before browser capture and are not recorded as resources, screenshots, or network evidence. Passwords are never typed into the site's browser JavaScript. The native session keeps cookies in an in-memory jar. Separate probes, downloads, robots, and sitemap requests use that session.

During browser capture, request interception supplies session cookies only to the exact target origin. Other origins, including another port on the same host and the local replay server, do not receive them. Response interception removes Set-Cookie before the browser receives it and updates the in-memory jar. The browser runs in private mode with disk caching and password saving disabled. Driver logs are disabled for authenticated operations. Browser requests are restricted to GET and HEAD; a background POST or another method stops this mode.

The manifest records only that authentication was required and the form-login method. Credentials, cookie jars, login transactions, and login settings are not saved for later sessions. Cleanup clears the jar and sensitive working buffers, discards credential references, closes the HTTP/browser sessions, and removes the temporary browser profile on normal shutdown. Python and the operating system do not provide a guarantee of forensic erasure of every former memory copy.

## Reflected login values

Before writing response bytes or manifest data, the tool checks known username, password, and cookie values and common textual encodings. It also checks rendered HTML and browser evidence before screenshots or diagnostic writes. A match aborts the operation with a fixed error message; it does not save the matched response or silently rewrite the original.

This is deliberately strict. A page displaying the exact entered username can stop capture. Captures still contain the private website content you requested, including account data unrelated to those known values. These checks are not a general sanitizer or a detector for every possible transformed value or secret rendered only inside an image. Use this mode only with a site whose handling of the supplied credentials you trust.

## Validation and replay

Authentication is discarded after each operation. To validate against the original again, log in again:

```sh
npm run validate -- --output captures/private --login --login-check '#signed-in'
```

Repeat any custom login URL/form/field options. Validation of an authenticated capture refuses to start without `--login`. Saved original baselines remain the comparison reference.

Each authenticated capture requires a fresh `--output` directory. Sessions and account identities are not persisted, so reusing an authenticated archive for a later account could mix private data. Public capture resume is unchanged. A failed authenticated attempt should be retried in a new output directory.

Status, local replay, and export need no original-site login because they read the captured files. The copied project does not implement the original account system. Its captured private content is readable by whoever has the directory. Export includes that content and evidence but carries no saved login session.

## Unsupported login flows

JavaScript-only login, JSON login APIs, external SSO/OAuth/SAML, MFA, CAPTCHA, HTTP Basic authentication, multipart forms, multi-step forms, and sites requiring JavaScript to read session cookies are unsupported by this mode. So are browser POST-based data APIs and captured HTML pages containing password controls. Failure remains explicit; the tool does not submit arbitrary forms, retry credentials, or guess additional authentication actions.

The existing limits on computed external requests and unavailable backend operations still apply after successful authentication. See [capture and replay](capture-and-replay.md#network-boundaries-and-limitations).
