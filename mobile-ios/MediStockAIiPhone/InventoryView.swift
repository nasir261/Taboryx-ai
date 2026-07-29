import SwiftUI

struct InventoryView: View {
    @EnvironmentObject private var model: AppViewModel

    var body: some View {
        NavigationStack {
            List {
                Section {
                    TextField("Search items", text: $model.searchText)
                }

                ForEach(model.filteredInventory) { item in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(item.name).font(.headline)
                            Spacer()
                            Text(item.status).font(.caption.bold()).padding(.horizontal, 8).padding(.vertical, 4).background(.blue.opacity(0.15), in: Capsule())
                        }
                        Text("\(item.category) • Qty \(item.quantity) • Min \(item.minimumQuantity)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(item.barcode).font(.caption2).foregroundStyle(.secondary)
                        if let expiryDate = item.expiryDate {
                            Text("Expiry: \(expiryDate)").font(.caption2).foregroundStyle(.secondary)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            .navigationTitle("Inventory")
        }
    }
}

