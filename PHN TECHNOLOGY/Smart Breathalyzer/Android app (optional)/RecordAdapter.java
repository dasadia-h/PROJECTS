package com.asvi.breathalyzer;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import java.util.List;

// adapter that powers both the Records and Violations recycler views
public class RecordAdapter extends RecyclerView.Adapter<RecordAdapter.RecordViewHolder> {

    private List<Record> records;

    public RecordAdapter(List<Record> records) {
        this.records = records;
    }

    @NonNull
    @Override
    public RecordViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
            .inflate(R.layout.item_record, parent, false);
        return new RecordViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull RecordViewHolder holder, int position) {
        Record record = records.get(position);
        holder.nameText.setText(record.getName() + record.getSurname());
        holder.licenseText.setText(record.getLicenseNumber());
        holder.drunkCountText.setText("Drunk Count: " + record.getDrunkCount());
        holder.vehicleText.setText(record.getVehicleNumber());
        holder.emailText.setText(record.getEmail());
        holder.locationText.setText(record.getLocation() + record.getTimestamp());
        holder.concentrationText.setText("Concentration: " + record.getConcentration());
    }

    @Override
    public int getItemCount() {
        return records.size();
    }

    static class RecordViewHolder extends RecyclerView.ViewHolder {
        TextView nameText, licenseText, drunkCountText, vehicleText,
                 emailText, locationText, concentrationText;

        public RecordViewHolder(@NonNull View itemView) {
            super(itemView);
            nameText          = itemView.findViewById(R.id.nameText);
            licenseText       = itemView.findViewById(R.id.licenseText);
            drunkCountText    = itemView.findViewById(R.id.drunkCountText);
            vehicleText       = itemView.findViewById(R.id.vehicleText);
            emailText         = itemView.findViewById(R.id.emailText);
            locationText      = itemView.findViewById(R.id.locationText);
            concentrationText = itemView.findViewById(R.id.concentrationText);
        }
    }
}
