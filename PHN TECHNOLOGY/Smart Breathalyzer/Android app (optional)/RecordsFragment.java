package com.asvi.breathalyzer;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

import java.util.ArrayList;
import java.util.List;

public class RecordsFragment extends Fragment {

    private RecyclerView recyclerView;
    private RecordAdapter adapter;
    private List<Record> recordList = new ArrayList<>();

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_records, container, false);

        recyclerView = view.findViewById(R.id.recordsRecyclerView);
        recyclerView.setLayoutManager(new LinearLayoutManager(getContext()));
        adapter = new RecordAdapter(recordList);
        recyclerView.setAdapter(adapter);

        loadAllRecords();
        return view;
    }


    // pull all records from Firebase and display them
    private void loadAllRecords() {
        FirebaseDatabase.getInstance().getReference("records")
            .addValueEventListener(new ValueEventListener() {
                @Override
                public void onDataChange(@NonNull DataSnapshot snapshot) {
                    recordList.clear();
                    for (DataSnapshot entry : snapshot.getChildren()) {
                        Record record = entry.getValue(Record.class);
                        if (record != null) recordList.add(record);
                    }
                    adapter.notifyDataSetChanged();
                }

                @Override
                public void onCancelled(@NonNull DatabaseError error) {
                    Toast.makeText(getContext(), "failed to load records", Toast.LENGTH_SHORT).show();
                }
            });
    }
}
