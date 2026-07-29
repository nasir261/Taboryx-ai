import SwiftUI

struct RootView: View {
    @EnvironmentObject private var model: AppViewModel

    var body: some View {
        Group {
            if model.session.isLoggedIn {
                tabView
            } else {
                LoginView()
            }
        }
        .task {
            if model.session.isLoggedIn, model.dashboard == nil {
                await model.loadAll()
            }
        }
    }

    private var tabView: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "square.grid.2x2") }

            InventoryView()
                .tabItem { Label("Inventory", systemImage: "list.bullet.rectangle") }

            ScanView()
                .tabItem { Label("Scan", systemImage: "barcode.viewfinder") }

            ReportsView()
                .tabItem { Label("Reports", systemImage: "chart.bar") }

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
    }
}

