import SwiftUI

struct ReportsView: View {
    var body: some View {
        NavigationStack {
            List {
                Section("Export") {
                    Label("Inventory CSV", systemImage: "doc.text")
                    Label("Inventory PDF", systemImage: "doc.richtext")
                    Label("Movements Excel", systemImage: "tablecells")
                }

                Section("Intelligence") {
                    Label("Low stock forecast", systemImage: "chart.line.uptrend.xyaxis")
                    Label("Expiry risk", systemImage: "clock.badge.exclamationmark")
                }
            }
            .navigationTitle("Reports")
        }
    }
}

