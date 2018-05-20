    /**
     * @name useFetch
     * @desc Make a network request and return (possible) data from server
     *       This is used to communicate with Contakti server
     * @example
     *       Basic use case:
     *            useFetch('https://data.foo.com/users','GET')
     *        This would get a list of users, as JSON object.
     *        Request contains no body.
     *        GET method used. (Alternatives: PUT, GET, FETCH, etc...)
     *
     * @returns Returns either JSON (data)
     *          or a error code defined in "globals" enum 'NetworkStatus'
     */
    static useFetch(url: string, method: string, reqData?: any): any {
        // Prepare all data for fetch envelope
        const headers = {
            Accept: 'application/json',
        }

        const state = Services.getStore().getState()

        // Append the cookies
        const session = state.session
        if (session.cookies) {
            headers['Cookie'] = session.cookies
        }

        // Append the auth headers
        const user = state.user
        if (user && user.email && session.authToken) {
            headers['X-Auth-Email'] = user.email
            headers['X-Auth-Token'] = session.authToken
        }

        let targetURL = NetConfig.serverURL
        if (NetConfig.serverPort &&
            NetConfig.serverPort !== 80 &&
            NetConfig.serverPort !== 443
        ) {
            targetURL = `${targetURL}:${NetConfig.serverPort}`
        }
        targetURL = `${targetURL}${NetConfig.serverAPIBase}${url}`

        let wholeEnvelope = undefined

        if (method === 'GET') {
            wholeEnvelope = { method }
        } else {
            const preparedData = Services.prepareFormData(reqData)
            const data = new FormData()
            for (const key in preparedData) {
                data.append(key, preparedData[key])
            }
            // For PUT, etc..
            wholeEnvelope = {
                method,
                headers,
                body: data,
            }
        }

        return fetch(targetURL, wholeEnvelope)
            .catch ((error) => {
                console.log('In error .catch, outputting error object:')
                console.log(error)
            })
    }

    /**
     * Returns a string representation of a key-value pairs
     * in a 'pojo'. This function flattens the pojo's structure in a proper
     * way and supports infinite depth. Use this to make a key-value
     * pair list to be put into Contakti API 'POST' request.
     *
     * @example prepareFormData( user: { x: val1,  y: val2} )
     */
    static prepareFormData(pojo: object, keyprefix?: string[]): object {
        const finalData = { }
        if (!pojo) { return finalData }

        for (let key in pojo) {
            const oval = pojo[key]
            if (typeof oval === 'object') {
                let subkeyPrefix = keyprefix ? keyprefix.slice() : []
                if (!subkeyPrefix) { subkeyPrefix = [] }
                subkeyPrefix.push(key)

                Object.assign(finalData, this.prepareFormData(oval, subkeyPrefix))
            } else {
                if (keyprefix) {
                    const currentKey = key
                    key = ''
                    keyprefix.forEach((subkey, ind) => {
                        if (ind === 0) {
                            key += subkey
                        } else {
                            key += `[${subkey}]`
                        }
                    })
                    key += `[${currentKey}]`
                }
                finalData[key] = oval
            }
        }
        return finalData
    }


