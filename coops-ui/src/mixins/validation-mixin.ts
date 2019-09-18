import { Component, Vue } from 'vue-property-decorator'
import { helpers, required, minLength, maxLength, ValidationRule } from 'vuelidate/lib/validators'

/**
 * Mixin that provides some useful schema validation utilities.
 */
@Component
export default class ValidationMixin extends Vue {
  /**
   * Creates a Vuelidate validation object to compute form validity.
   * @param schemaObject The schema object to use.
   * @param value The name of the value we are validating.
   * @returns A Vuelidate validation rules object.
   */
  public createVuelidateValidationObject (schemaObject: object, value: string): any {
    let obj = {}

    // ensure schema object is initialized
    if (schemaObject && schemaObject[value]) {
      // create node for value
      obj[value] = {}
      // iterate over schema object properties
      Object.keys(schemaObject[value])
        .forEach(prop => {
          // create node for each validation property
          obj[value][prop] = {}
          // iterate over validation property params
          Object.keys(schemaObject[value][prop])
            .forEach(param => {
              // add specified validation rules to array
              switch (param) {
                case 'type': break // ignore for now
                case 'required':
                  obj[value][prop].required = required
                  break
                case 'minLength':
                  obj[value][prop].minLength = minLength.call(this, schemaObject[value][prop].minLength)
                  break
                case 'maxLength':
                  obj[value][prop].maxLength = maxLength.call(this, schemaObject[value][prop].maxLength)
                  break
                // FUTURE: add extra validation rules here
                default: break
              }
            })
        })
    }

    // sample return object
    // addressLocal: {
    //   streetAddress: {
    //     required,
    //     minLength: minLength(this.schemaObject.addressLocal.streetAddress.minLength),
    //     maxLength: maxLength(this.schemaObject.addressLocal.streetAddress.maxLength)
    //   },
    //   ...
    // }

    return obj
  }

  /**
   * Custom Vuelidate rule for validating that the subject value is Canada.
   * @todo Use this at some point.
   */
  protected isCanada = (): ValidationRule => {
    return helpers.withParams(
      { type: 'isCanada' },
      (value) => value && value === 'CA'
    )
  }

  /**
   * Creates a Vuetify validation rules object from the Vuelidate state.
   * @param value The name of the value we are validating.
   * @returns A Vuetify validation rules object.
   */
  public createVuetifyRulesObject (value: string): { [attr: string]: Array<Function> } {
    let obj = {}

    // ensure Vuelidate state object is initialized
    if (this.$v && this.$v[value]) {
      // iterate over Vuelidate object properties
      Object.keys(this.$v[value])
        // only look at validation properties
        .filter(prop => prop.charAt(0) !== '$')
        .forEach(prop => {
          // create array for each validation property
          obj[prop] = []
          // iterate over validation property params
          Object.keys(this.$v[value][prop].$params)
            .forEach(param => {
              // add specified validation functions to array
              switch (param) {
                case 'required': obj[prop].push(() => this.requiredRule(value, prop)); break
                case 'minLength': obj[prop].push(() => this.minLengthRule(value, prop)); break
                case 'maxLength': obj[prop].push(() => this.maxLengthRule(value, prop)); break
                // FUTURE: add extra validation functions here
                // case 'isCanada': rules[prop].push(() => this.isCanadaRule(value, prop)); break
                default: break
              }
            })
        })
    }

    // sample return object
    // streetAddress: [
    //   () => this.requiredRule('addressLocal', 'streetAddress'),
    //   () => this.minLengthRule('addressLocal', 'streetAddress'),
    //   () => this.maxLengthRule('addressLocal', 'streetAddress')
    // ],
    // ...

    return obj
  }

  /**
   * Generic Vuetify validation rules.
   * @param prop The name of the property object to validate.
   * @param key The name of the property key (field) to validate.
   * @returns True if the rule passes, otherwise an error string.
   */
  protected requiredRule (prop: string, key: string): boolean | string {
    return (this.$v[prop] && this.$v[prop][key].required) || 'This field is required'
  }

  protected minLengthRule (prop: string, key: string): boolean | string {
    const min = this.$v[prop][key].$params.minLength.min
    return (this.$v[prop] && this.$v[prop][key].minLength) || `Minimum length is ${min}`
  }

  protected maxLengthRule (prop: string, key: string): boolean | string {
    const max = this.$v[prop][key].$params.maxLength.max
    return (this.$v[prop] && this.$v[prop][key].maxLength) || `Maximum length is ${max}`
  }

  protected isCanadaRule (prop: string, key: string): boolean | string {
    return (this.$v[prop] && this.$v[prop][key].isCanada) || `Address must be in Canada`
  }

  /**
   * Creates a schema validation object from the schema object promise.
   * @param arr An array with a promise that returns the schema object.
   * @param value The name of the value we are validating.
   * @returns A schema validation object.
   */
  public async createSchemaValidationObject (arr: Array<Promise<any>>, value: string): Promise<{}> {
    let obj = {}

    // ensure parameter is valid
    if (arr && arr.length > 0) {
      // resolve the promise
      await arr[0].then(schema => {
        // create node for value
        obj[value] = {}

        Object.keys(schema.properties).forEach(key => {
          // create node for property
          obj[value][key] = {}
          // populate misc property validators
          const prop = schema.properties[key]
          if (prop.type) obj[value][key].type = prop.type
          if (prop.minLength) obj[value][key].minLength = prop.minLength
          if (prop.maxLength) obj[value][key].maxLength = prop.maxLength
          // FUTURE: add extra validators here
        })

        // populate 'required' validators
        schema.required.forEach(key => {
          obj[value][key].required = true
        })
      })
    }

    return obj
  }
}
