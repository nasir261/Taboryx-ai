import SwiftUI

struct ScanView: View {
    @EnvironmentObject private var model: AppViewModel
    @State private var code = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Barcode / QR") {
                    TextField("Enter or scan code", text: $code)
                    Button("Simulate Scan") {
                        Task { await model.performScan(code) }
                    }
                }

                Section("Result") {
                    Text(model.scanResult)
                }
            }
            .navigationTitle("Scan")
        }
    }
}

