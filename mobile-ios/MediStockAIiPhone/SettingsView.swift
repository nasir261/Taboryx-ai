import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var model: AppViewModel

    var body: some View {
        NavigationStack {
            Form {
                Section("Backend") {
                    TextField("API Base URL", text: $model.apiBaseURLText)
                    Text("Use your desktop machine's IP address on a real iPhone.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Session") {
                    LabeledContent("User", value: model.session.username)
                    LabeledContent("Role", value: model.session.role)
                    Button("Log Out", role: .destructive) {
                        model.logout()
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}

