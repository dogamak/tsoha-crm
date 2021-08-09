<template>
    <div>
        <DatePicker v-model="value" />
        <input type="hidden" :name="fieldName" :value="timestamp" />
    </div>
</template>

<script>
    import DatePicker from 'vue2-datepicker';
    import 'vue2-datepicker/index.css';

    export default {
        components: { DatePicker },

        props: {
            initialValue: String,
            fieldName: String,
        },

        data () {
            let value = this.initialValue;

            if (typeof value === 'string') {
                value = new Date(value);
            }

            return {
                value,
            };
        },

        computed: {
            timestamp () {
                return this.value ? this.value.toISOString() : '';
            },
        },
    };
</script>
