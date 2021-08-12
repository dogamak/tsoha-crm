<template>
    <div class="card">
        <div class="card-header">
            <div class="d-flex align-items-center justify-content-between">
                <span></span>
                <button class="btn btn-sm btn-primary" name="__action" :value="`${fieldName}.create_new`">Luo uusi</button>
            </div>
        </div>
        <div>
            <table class="table mb-0 user-management-table">
                <tr v-for="row in rows" :key="row.id">
                    <td style="width: 2.54rem" class="text-center border-end">
                        <input
                            type="checkbox"
                            @change="onRowSelectChange($event, row)"
                        />
                    </td>
                    <td><a :href="`/view/${row.id}`">{{ row.title }}</a></td>
                </tr>
            </table>
        </div>
        <div class="card-footer">
            <div class="d-flex align-items-center justify-content-between">
                <div class="text-secondary" style="font-size: 0.9rem">
                    <template v-if="selected.length > 0">
                        Selected {{ selected.length }} out of {{ rows.length }}
                    </template>
                </div>
                <div class="d-flex">
                    <input type="hidden" :name="`${fieldName}.selected`" :value="selected.join(',')" />
                    <button class="btn btn-sm btn-danger me-2" type="submit" name="__action" :value="`${fieldName}.remove_selected`">Poista valitut</button>
                    <button class="btn btn-sm btn-primary" name="__action" :value="`${fieldName}.create_new`">Luo uusi</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
    export default {
        props: {
            fieldName: String,
            resourceType: String,
            rows: Array,
        },

        data () {
            return {
                selected: [],
            };
        },

        methods: {
            onRowSelectChange (evt, row) {
                if (evt.target.checked) {
                    this.selected.push(row.id);
                } else {
                    const i = this.selected.indexOf(row.id);
                    this.selected.splice(i, 1);
                }
            },
        },
    };
</script>

<style lang="scss">
    td {
        height: 2.5rem;
    }

    table {
        min-height: 2.5rem;
    }

    tr:not(:last-child) {
        border-bottom: 1px solid #dfdfdf;
    }
</style>
