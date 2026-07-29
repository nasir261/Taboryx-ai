import SwiftUI

struct LoginView: View {
    @EnvironmentObject private var model: AppViewModel

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Spacer()
                Text(AppConfiguration.appName)
                    .font(.largeTitle.bold())
                Text("Sign in to sync with the desktop database.")
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                VStack(spacing: 12) {
                    TextField("Username", text: $model.loginUsername)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textFieldStyle(.roundedBorder)
                    SecureField("Password", text: $model.loginPassword)
                        .textFieldStyle(.roundedBorder)
                    TextField("API Base URL", text: $model.apiBaseURLText)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textFieldStyle(.roundedBorder)
                }

                if let errorMessage = model.errorMessage {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                        .font(.footnote)
                }

                Button {
                    Task { await model.login() }
                } label: {
                    Text("Sign In")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)

                Spacer()
            }
            .padding()
        }
    }
}

