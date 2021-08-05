<template>
    <div class="resource-select" @blur="open = false">
        <input type="hidden" :name="name" :value="selected.id" v-if="name && selected" />
        <div class="cover" @click="open = !open" tabindex="0" @keydown.enter="open = !open">
            <div class="cover-content" v-if="selected !== null">
                <span class="option-title">{{ selected.title }}</span>
                <span class="option-type">{{ selected.type }}</span>
            </div>
            <div class="cover-content" v-else>
                <span class="text-secondary">Click to select</span>
            </div>
            <div class="cover-tip">
                <div class="icon" :class="{ rotate: open }">
                    <i class="bi-chevron-right"></i>
                </div>
            </div>
        </div>
        <div class="drawer" v-if="open">
            <input type="text" class="filter" placeholder="Filter..." :value="filter" @input="onFilterChange" />
            <div class="options">
                <div class="option" tabindex="0" @keydown.enter="selected = option; open = false" @focus="focused = index" :class="{ focused: focused === index }" v-for="(option, index) in filteredOptions" key="option.id" @click="selected = option; open = false">
                    <span class="option-title" v-html="highlightFilter(option.title)"></span>
                    <span class="option-type">{{ option.type }}</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
    export default {
        props: {
            name: String,
            options: Array,
        },

        data () {
            return {
                selected: null,
                open: false,
                filter: '',
                focused: -1,
            };
        },

        mounted () {
            this._globalEventListener = (evt) => {
                if (!this.$el.contains(evt.target) && this.$el !== evt.target) {
                    this.onClickOutside();
                }
            };

            document.addEventListener('click', this._globalEventListener);
        },

        unmounted () {
            document.removeEventListener('click', this._globalEventListener);
        },

        methods: {
            onFilterChange (evt) {
                this.filter = evt.target.value;
            },

            highlightFilter (text) {
                if (this.filter === '') {
                    return text;
                }

                return text.replace(this.filter, '<b class="highlight-filter">' + this.filter + '</b>');
            },

            onClickOutside () {
                this.open = false;
            },
        },

        computed: {
            filteredOptions () {
                if (this.filter === '') {
                    return this.options;
                }

                return this.options.filter((option) => option.title.indexOf(this.filter) !== -1);
            },
        },
    };
</script>

<style lang="scss" scoped>
    $option-height: 3rem; 

    .resource-select {
        border: 1px solid #dfdfdf;
        border-radius: 0.25rem;
        position: relative;

        .cover {
            padding: 0.25rem 0.75rem;
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
            height: $option-height;

            .cover-content {
                display: flex;
                flex-direction: column;
            }

            .cover-tip {
                display: flex;
                flex-direction: row;
                align-items: center;

                .icon {
                    transition-duration: 200ms;
                }
            }
        }

        .drawer {
            position: absolute;
            top: $option-height - 0.25rem;
            left: -1px;
            right: -1px;
            border: 1px solid #dfdfdf;
            border-top: none;
            border-bottom-left-radius: 0.25rem;
            border-bottom-right-radius: 0.25rem;
            padding-top: 0.25rem;
            background-color: white;

            .filter {
                width: 100%;
                height: 2.5rem;
                border: none;
                border-top: 1px solid #dfdfdf;
                border-bottom: 1px solid #dfdfdf;
                background-color: #f8f9fa;
                padding: 0 0.75rem;
            }

            .options {
                max-height: $option-height * 4.5;
                overflow-y: scroll;
                scrollbar-width: thin;

                .option {
                    height: $option-height;
                    display: flex;
                    flex-direction: column;
                    padding: 0.5rem 0.75rem;
                    justify-content: center;

                    &:not(:last-child) {
                        border-bottom: 1px solid #f5f5f5;
                    }

                    &:hover, &:focus {
                        background-color: #f8f9fa;
                    }
                }
            }
        }

        .cover-content, .option {
            border-radius: 0.25rem;
        }

        .option-type {
            font-size: 0.7rem;
            letter-spacing: 0.05em;
            color: #f00;
            margin-top: -0.3rem;
            font-weight: 600;
            padding-bottom: 0.2rem;
        }
    }

    .rotate {
        transform: rotate(-90deg);
    }
</style>
