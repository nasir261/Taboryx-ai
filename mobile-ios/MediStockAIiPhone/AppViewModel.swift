import Foundation
import SwiftUI

@MainActor
final class AppViewModel: ObservableObject {
    @Published var session = SessionInfo()
    @Published var dashboard: DashboardSummary?
    @Published var inventoryItems: [InventoryItem] = []
    @Published var movements: [MovementItem] = []
    @Published var scanResult: String = "Ready to scan."
    @Published var searchText: String = ""
    @Published var apiBaseURLText: String = AppConfiguration.defaultAPIBaseURL.absoluteString
    @Published var loginUsername: String = ""
    @Published var loginPassword: String = ""
    @Published var errorMessage: String?

    private let api = APIClient()

    func login() async {
        do {
            api.baseURL = URL(string: apiBaseURLText) ?? AppConfiguration.defaultAPIBaseURL
            let response = try await api.login(username: loginUsername, password: loginPassword)
            session.username = response.user.username
            session.role = response.user.role
            session.isLoggedIn = true
            session.authToken = response.token
            errorMessage = nil
            await loadAll()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func logout() {
        session = SessionInfo()
        dashboard = nil
        inventoryItems = []
        movements = []
        api.authToken = nil
    }

    func loadAll() async {
        do {
            async let dash = api.fetchDashboardSummary()
            async let inventory = api.fetchInventoryItems()
            async let recentMovements = api.fetchMovements()

            dashboard = try await dash
            inventoryItems = try await inventory
            movements = try await recentMovements
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func performScan(_ code: String) async {
        do {
            let result = try await api.sendScan(code: code)
            scanResult = result.message
        } catch {
            scanResult = error.localizedDescription
        }
    }

    var filteredInventory: [InventoryItem] {
        guard !searchText.isEmpty else { return inventoryItems }
        let query = searchText.lowercased()
        return inventoryItems.filter {
            $0.name.lowercased().contains(query) ||
            $0.category.lowercased().contains(query) ||
            $0.barcode.lowercased().contains(query)
        }
    }
}

